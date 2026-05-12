import pytest
from fastapi import HTTPException

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.stock_transfer import StockTransferStatus, LOCATION_INTERNAL, LOCATION_ML_FULL
from src.schemas.product import ProductCreate
from src.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferItemCreate,
    StockTransferReceiveItem,
    StockTransferUpdate,
)
from src.services.inventory_service import inventory_service
from src.services.stock_transfer_service import stock_transfer_service

pytestmark = pytest.mark.db


def _make_product(db, sku: str):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Transfer Product {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _seed_internal_stock(db, product_id: int, qty: int):
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=qty,
        reason="seed",
        location=LOCATION_INTERNAL,
    )
    db.commit()


def _stock_at(db, product_id: int, location: str) -> int:
    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == product_id,
            InventoryItem.location == location,
        )
        .first()
    )
    return item.quantity if item else 0


def test_create_draft_transfer(db):
    product = _make_product(db, "ST-CREATE-1")
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    assert transfer.id is not None
    assert transfer.status == StockTransferStatus.DRAFT.value
    assert transfer.source_location == LOCATION_INTERNAL
    assert transfer.dest_location == LOCATION_ML_FULL
    assert len(transfer.items) == 1
    assert transfer.items[0].qty_planned == 10


def test_create_draft_rejects_same_source_and_dest(db):
    product = _make_product(db, "ST-SAME-LOC")
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.create_draft(
            db=db,
            transfer_in=StockTransferCreate(
                source_location=LOCATION_INTERNAL,
                dest_location=LOCATION_INTERNAL,
                items=[StockTransferItemCreate(product_id=product.id, qty_planned=5)],
            ),
        )
    assert exc.value.status_code == 400


def test_create_draft_rejects_zero_quantity(db):
    product = _make_product(db, "ST-ZERO-QTY")
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.create_draft(
            db=db,
            transfer_in=StockTransferCreate(
                dest_location=LOCATION_ML_FULL,
                items=[StockTransferItemCreate(product_id=product.id, qty_planned=0)],
            ),
        )
    assert exc.value.status_code == 400


def test_ship_moves_stock_out_of_source(db):
    product = _make_product(db, "ST-SHIP-1")
    _seed_internal_stock(db, product.id, 50)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=20)],
        ),
    )
    shipped = stock_transfer_service.ship(db=db, transfer_id=transfer.id)

    assert shipped.status == StockTransferStatus.SHIPPED.value
    assert shipped.shipped_at is not None
    assert shipped.items[0].qty_shipped == 20

    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 30
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 0


def test_ship_blocks_when_insufficient_stock(db):
    product = _make_product(db, "ST-SHIP-LOW")
    _seed_internal_stock(db, product.id, 5)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    assert exc.value.status_code == 400
    assert "Insufficient stock" in exc.value.detail
    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 5


def test_ship_rejects_non_draft(db):
    product = _make_product(db, "ST-RE-SHIP")
    _seed_internal_stock(db, product.id, 50)
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    assert exc.value.status_code == 400


def test_ship_rejects_empty_transfer(db):
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(dest_location=LOCATION_ML_FULL, items=[]),
    )
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    assert exc.value.status_code == 400


def test_full_receive_moves_stock_to_destination(db):
    product = _make_product(db, "ST-RECV-FULL")
    _seed_internal_stock(db, product.id, 30)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=20)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)

    received = stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[
            StockTransferReceiveItem(product_id=product.id, quantity=20),
        ],
    )
    assert received.status == StockTransferStatus.RECEIVED.value
    assert received.received_at is not None
    assert received.items[0].qty_received == 20
    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 10
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 20


def test_partial_receive_then_complete(db):
    product = _make_product(db, "ST-RECV-PART")
    _seed_internal_stock(db, product.id, 30)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=20)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)

    partial = stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=12)],
    )
    assert partial.status == StockTransferStatus.PARTIALLY_RECEIVED.value
    assert partial.items[0].qty_received == 12
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 12

    final = stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=8)],
    )
    assert final.status == StockTransferStatus.RECEIVED.value
    assert final.items[0].qty_received == 20
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 20


def test_receive_blocks_over_shipped(db):
    product = _make_product(db, "ST-RECV-OVER")
    _seed_internal_stock(db, product.id, 30)
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)

    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.receive_items(
            db=db,
            transfer_id=transfer.id,
            received_items=[StockTransferReceiveItem(product_id=product.id, quantity=15)],
        )
    assert exc.value.status_code == 400


def test_receive_rejects_draft(db):
    product = _make_product(db, "ST-RECV-DRAFT")
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.receive_items(
            db=db,
            transfer_id=transfer.id,
            received_items=[StockTransferReceiveItem(product_id=product.id, quantity=5)],
        )
    assert exc.value.status_code == 400


def test_cancel_only_from_draft(db):
    product = _make_product(db, "ST-CANCEL")
    _seed_internal_stock(db, product.id, 30)
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    cancelled = stock_transfer_service.cancel(db=db, transfer_id=transfer.id)
    assert cancelled.status == StockTransferStatus.CANCELLED.value
    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 30

    other = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=5)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=other.id)
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.cancel(db=db, transfer_id=other.id)
    assert exc.value.status_code == 400


def test_update_draft_replaces_items(db):
    a = _make_product(db, "ST-UPD-A")
    b = _make_product(db, "ST-UPD-B")
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=a.id, qty_planned=5)],
        ),
    )
    updated = stock_transfer_service.update_draft(
        db=db,
        transfer_id=transfer.id,
        transfer_in=StockTransferUpdate(
            notes="updated",
            items=[
                StockTransferItemCreate(product_id=a.id, qty_planned=7),
                StockTransferItemCreate(product_id=b.id, qty_planned=3),
            ],
        ),
    )
    assert updated.notes == "updated"
    qty_by_product = {item.product_id: item.qty_planned for item in updated.items}
    assert qty_by_product == {a.id: 7, b.id: 3}


def test_update_draft_rejects_after_ship(db):
    product = _make_product(db, "ST-UPD-LOCK")
    _seed_internal_stock(db, product.id, 30)
    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.update_draft(
            db=db,
            transfer_id=transfer.id,
            transfer_in=StockTransferUpdate(notes="too late"),
        )
    assert exc.value.status_code == 400
