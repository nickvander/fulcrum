"""
Slice-3 tests: allocation planner (multi-destination draft creation),
inventory snapshot for planning, and reconciliation report for shrinkage.
"""
import pytest
from fastapi import HTTPException

from src.crud import crud_product
from src.models.stock_transfer import (
    LOCATION_AMAZON_FBA,
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransferStatus,
)
from src.schemas.product import ProductCreate
from src.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferItemCreate,
    StockTransferReceiveItem,
)
from src.services.inventory_service import inventory_service
from src.services.stock_transfer_service import stock_transfer_service


pytestmark = pytest.mark.db


def _make_product(db, sku: str):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Planner Product {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _seed_internal(db, product_id: int, qty: int):
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=qty,
        reason="seed",
        location=LOCATION_INTERNAL,
    )
    db.commit()


def test_inventory_snapshot_breaks_down_by_location(db):
    a = _make_product(db, "SNAP-A")
    b = _make_product(db, "SNAP-B")
    _seed_internal(db, a.id, 50)
    _seed_internal(db, b.id, 30)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=a.id, qty_planned=20)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=a.id, quantity=20)],
    )

    snapshot = stock_transfer_service.get_inventory_snapshot(
        db=db, product_ids=[a.id, b.id]
    )
    rows = {row["product_id"]: row for row in snapshot}
    assert rows[a.id]["by_location"][LOCATION_INTERNAL] == 30
    assert rows[a.id]["by_location"][LOCATION_ML_FULL] == 20
    assert rows[a.id]["total"] == 50
    assert rows[b.id]["by_location"][LOCATION_INTERNAL] == 30
    assert rows[b.id]["by_location"][LOCATION_ML_FULL] == 0


def test_plan_allocations_creates_one_draft_per_destination(db):
    a = _make_product(db, "PLAN-A")
    b = _make_product(db, "PLAN-B")
    _seed_internal(db, a.id, 100)
    _seed_internal(db, b.id, 100)

    drafts = stock_transfer_service.plan_allocations(
        db=db,
        allocations=[
            {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 30},
            {"product_id": a.id, "dest_location": LOCATION_AMAZON_FBA, "qty_planned": 20},
            {"product_id": b.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 10},
        ],
        notes="Q2 allocation",
    )

    assert len(drafts) == 2
    by_dest = {d.dest_location: d for d in drafts}
    assert by_dest[LOCATION_ML_FULL].notes == "Q2 allocation"
    ml_items = {item.product_id: item.qty_planned for item in by_dest[LOCATION_ML_FULL].items}
    assert ml_items == {a.id: 30, b.id: 10}
    az_items = {item.product_id: item.qty_planned for item in by_dest[LOCATION_AMAZON_FBA].items}
    assert az_items == {a.id: 20}
    for draft in drafts:
        assert draft.status == StockTransferStatus.DRAFT.value


def test_plan_allocations_combines_duplicate_destination_entries(db):
    a = _make_product(db, "PLAN-DUP")
    _seed_internal(db, a.id, 40)

    drafts = stock_transfer_service.plan_allocations(
        db=db,
        allocations=[
            {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 10},
            {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 15},
        ],
    )
    assert len(drafts) == 1
    assert drafts[0].items[0].qty_planned == 25


def test_plan_allocations_rejects_over_internal_stock(db):
    a = _make_product(db, "PLAN-OVER")
    _seed_internal(db, a.id, 10)
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.plan_allocations(
            db=db,
            allocations=[
                {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 12},
            ],
        )
    assert exc.value.status_code == 400


def test_plan_allocations_rejects_internal_destination(db):
    a = _make_product(db, "PLAN-SELF")
    _seed_internal(db, a.id, 50)
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.plan_allocations(
            db=db,
            allocations=[
                {"product_id": a.id, "dest_location": LOCATION_INTERNAL, "qty_planned": 5},
            ],
        )
    assert exc.value.status_code == 400


def test_reconciliation_lists_only_delta_lines(db):
    clean = _make_product(db, "REC-CLEAN")
    shrink = _make_product(db, "REC-SHRINK")
    _seed_internal(db, clean.id, 50)
    _seed_internal(db, shrink.id, 50)

    # Clean transfer: shipped == received, should NOT appear.
    t_clean = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=clean.id, qty_planned=20)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=t_clean.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=t_clean.id,
        received_items=[StockTransferReceiveItem(product_id=clean.id, quantity=20)],
    )

    # Shrinkage transfer: shipped 20, received 17.
    t_shrink = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=shrink.id, qty_planned=20)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=t_shrink.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=t_shrink.id,
        received_items=[StockTransferReceiveItem(product_id=shrink.id, quantity=17)],
    )

    report = stock_transfer_service.get_reconciliation_report(db=db)
    transfer_ids = [r["transfer_id"] for r in report]
    assert t_shrink.id in transfer_ids
    assert t_clean.id not in transfer_ids

    row = next(r for r in report if r["transfer_id"] == t_shrink.id)
    assert row["qty_shipped"] == 20
    assert row["qty_received"] == 17
    assert row["delta"] == -3
