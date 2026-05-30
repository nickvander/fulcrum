"""Stock-movement audit: reversible inventory adjustments.

Covers `inventory_service.reverse_adjustment` + the
`POST /reports/inventory-adjustments/{id}/reverse` endpoint + the
reversal linkage surfaced by the list endpoint, plus the
`marketplace_sync` reason code added in the same slice.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import (
    InventoryAdjustment,
    InventoryAdjustmentReasonCode,
    InventoryItem,
)
from src.schemas.product import ProductCreate
from src.services.inventory_service import (
    AdjustmentReversalError,
    inventory_service,
)


pytestmark = pytest.mark.db

_N = {"i": 0}


def _product(db: Session):
    _N["i"] += 1
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"REV {_N['i']}", sku=f"REV-{_N['i']}",
            cost_price=10.0, default_resale_price=25.0,
        ),
    )


def _seed_adjustment(db, product, *, delta, reason_code, user="operator@example.com"):
    _item, adj = inventory_service.record_adjustment(
        db, product_id=product.id, adjustment=delta,
        reason="seed", reason_code=reason_code, location="default", user_id=user,
    )
    db.commit()
    db.refresh(adj)
    return adj


def _qty(db, product_id, location="default") -> int:
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product_id, InventoryItem.location == location)
        .first()
    )
    return item.quantity if item else 0


# --------------------------------------------------------------------------- #
# Service: happy path + guardrails
# --------------------------------------------------------------------------- #


def test_reverse_manual_adjustment_restores_stock_and_links(db):
    p = _product(db)
    # Operator keys in a -5 shrinkage by mistake.
    adj = _seed_adjustment(db, p, delta=-5, reason_code=InventoryAdjustmentReasonCode.SHRINKAGE)
    assert _qty(db, p.id) == -5

    reversal = inventory_service.reverse_adjustment(db, adj.id, actor="boss@example.com")
    db.commit()

    # Equal-and-opposite correction restores stock to 0.
    assert reversal.adjustment == 5
    assert reversal.reason_code == InventoryAdjustmentReasonCode.CORRECTION.value
    assert reversal.reverses_adjustment_id == adj.id
    assert reversal.created_by == "boss@example.com"
    assert _qty(db, p.id) == 0
    # Backref wired both ways.
    db.refresh(adj)
    assert adj.reversed_by is not None
    assert adj.reversed_by.id == reversal.id


def test_reverse_includes_note_in_reason(db):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=3, reason_code=InventoryAdjustmentReasonCode.MANUAL)
    reversal = inventory_service.reverse_adjustment(
        db, adj.id, actor="op", note="duplicate entry",
    )
    db.commit()
    assert "duplicate entry" in (reversal.reason or "")
    assert f"#{adj.id}" in (reversal.reason or "")


def test_cannot_reverse_system_reason_code(db):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-2, reason_code=InventoryAdjustmentReasonCode.SALE)
    with pytest.raises(AdjustmentReversalError) as exc:
        inventory_service.reverse_adjustment(db, adj.id, actor="op")
    assert exc.value.code == "not_reversible"


def test_cannot_reverse_twice(db):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-4, reason_code=InventoryAdjustmentReasonCode.DAMAGE)
    inventory_service.reverse_adjustment(db, adj.id, actor="op")
    db.commit()
    with pytest.raises(AdjustmentReversalError) as exc:
        inventory_service.reverse_adjustment(db, adj.id, actor="op")
    assert exc.value.code == "already_reversed"


def test_cannot_reverse_a_reversal(db):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-4, reason_code=InventoryAdjustmentReasonCode.THEFT)
    reversal = inventory_service.reverse_adjustment(db, adj.id, actor="op")
    db.commit()
    db.refresh(reversal)
    with pytest.raises(AdjustmentReversalError) as exc:
        inventory_service.reverse_adjustment(db, reversal.id, actor="op")
    assert exc.value.code == "is_reversal"


def test_reverse_missing_adjustment_raises(db):
    with pytest.raises(AdjustmentReversalError) as exc:
        inventory_service.reverse_adjustment(db, 999999, actor="op")
    assert exc.value.code == "not_found"


# --------------------------------------------------------------------------- #
# marketplace_sync reason code (CHECK constraint admits it)
# --------------------------------------------------------------------------- #


def test_marketplace_sync_reason_code_persists(db):
    p = _product(db)
    inventory_service.adjust_stock(
        db, product_id=p.id, adjustment=7,
        reason_code=InventoryAdjustmentReasonCode.MARKETPLACE_SYNC,
        location="MercadoLibre", user_id="system",
    )
    db.commit()  # would raise IntegrityError if the CHECK rejected it
    row = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.product_id == p.id)
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )
    assert row.reason_code == "marketplace_sync"


# --------------------------------------------------------------------------- #
# Endpoint contract + list linkage
# --------------------------------------------------------------------------- #


def test_reverse_endpoint_happy_path(client, db, admin_headers):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-6, reason_code=InventoryAdjustmentReasonCode.RECOUNT)

    resp = client.post(
        f"/api/v1/reports/inventory-adjustments/{adj.id}/reverse",
        headers=admin_headers, json={"note": "miscount"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["adjustment"] == 6
    assert body["reason_code"] == "correction"
    assert body["reverses_adjustment_id"] == adj.id
    assert _qty(db, p.id) == 0


def test_reverse_endpoint_rejects_system_row(client, db, admin_headers):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-1, reason_code=InventoryAdjustmentReasonCode.CANCELLATION)
    resp = client.post(
        f"/api/v1/reports/inventory-adjustments/{adj.id}/reverse", headers=admin_headers,
    )
    assert resp.status_code == 409


def test_reverse_endpoint_404_for_missing(client, db, admin_headers):
    resp = client.post(
        "/api/v1/reports/inventory-adjustments/987654/reverse", headers=admin_headers,
    )
    assert resp.status_code == 404


def test_list_surfaces_reversal_linkage(client, db, admin_headers):
    p = _product(db)
    adj = _seed_adjustment(db, p, delta=-8, reason_code=InventoryAdjustmentReasonCode.MANUAL)

    # Before reversal: the row is reversible.
    body = client.get(
        f"/api/v1/reports/inventory-adjustments?product_id={p.id}", headers=admin_headers,
    ).json()
    row = next(r for r in body["rows"] if r["id"] == adj.id)
    assert row["reversible"] is True
    assert row["reversed_by_id"] is None
    assert row["reverses_adjustment_id"] is None

    # Reverse it, then the original is no longer reversible and the
    # correction row points back at it.
    inventory_service.reverse_adjustment(db, adj.id, actor="op")
    db.commit()

    body = client.get(
        f"/api/v1/reports/inventory-adjustments?product_id={p.id}", headers=admin_headers,
    ).json()
    by_id = {r["id"]: r for r in body["rows"]}
    original = by_id[adj.id]
    assert original["reversible"] is False
    assert original["reversed_by_id"] is not None

    reversal_row = by_id[original["reversed_by_id"]]
    assert reversal_row["reverses_adjustment_id"] == adj.id
    assert reversal_row["reversible"] is False  # a correction row isn't reversible
