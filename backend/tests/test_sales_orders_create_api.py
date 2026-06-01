"""FP-04: authenticated on-site sales-order create.

Exercises POST /api/v1/sales-orders/ end to end:

  * authoritative server-side pricing + correct total
  * per-line atomic stock decrement (FP-03) with -qty SALE audit rows
  * idempotent replay on `idempotency_key` (decrement happens ONCE)
  * all-or-nothing rollback: one short line on a multi-line order creates
    NO order and leaves the OTHER line's stock untouched
  * missing product → 404, empty/invalid payloads → 422, auth required
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.config import settings
from src.crud import crud_product
from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db

_BASE = f"{settings.API_V1_STR}/sales-orders/"
_N = {"i": 0}


def _product(db: Session, *, price: float, cost: float = 1.0) -> "object":
    _N["i"] += 1
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"OS {_N['i']}",
            sku=f"OS-{_N['i']}",
            default_resale_price=price,
            cost_price=cost,
        ),
    )


def _stock(db: Session, product, qty: int, *, location: str = "default") -> None:
    db.add(
        InventoryItem(product_id=product.id, variant_id=None, quantity=qty, location=location)
    )
    db.flush()


def _qty_on_hand(db: Session, product, *, location: str = "default") -> int:
    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == product.id,
            InventoryItem.variant_id.is_(None),
            InventoryItem.location == location,
        )
        .first()
    )
    return item.quantity if item else 0


def _sale_audit_rows(db: Session, product):
    return (
        db.query(InventoryAdjustment)
        .filter(
            InventoryAdjustment.product_id == product.id,
            InventoryAdjustment.reason_code == "sale",
        )
        .all()
    )


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_create_single_line_success(client: TestClient, db, test_product, admin_headers):
    _stock(db, test_product, 10)

    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "os-key-single",
            "items": [{"product_id": test_product.id, "quantity": 3}],
        },
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Priced authoritatively from the product (default_resale_price=19.99).
    assert body["total_price"] == pytest.approx(3 * 19.99)
    assert body["source"] == OrderSource.FULCRUM.value
    assert body["status"] == "COMPLETED"
    assert body["external_order_id"] == "os-key-single"
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["items"][0]["price_per_unit"] == pytest.approx(19.99)

    # Order + item persisted.
    order = db.query(SalesOrder).filter(SalesOrder.id == body["id"]).one()
    assert order.source == OrderSource.FULCRUM.value
    assert order.total_price == pytest.approx(3 * 19.99)
    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
    assert len(items) == 1

    # Stock decremented + a -qty SALE audit row written.
    assert _qty_on_hand(db, test_product) == 7
    rows = _sale_audit_rows(db, test_product)
    assert len(rows) == 1
    assert rows[0].adjustment == -3


def test_create_multi_line_success(client: TestClient, db, admin_headers):
    p1 = _product(db, price=100.0)
    p2 = _product(db, price=50.0)
    _stock(db, p1, 5)
    _stock(db, p2, 8)

    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "os-key-multi",
            "items": [
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 4},
            ],
        },
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["total_price"] == pytest.approx(2 * 100.0 + 4 * 50.0)
    assert len(body["items"]) == 2

    assert _qty_on_hand(db, p1) == 3
    assert _qty_on_hand(db, p2) == 4
    assert _sale_audit_rows(db, p1)[0].adjustment == -2
    assert _sale_audit_rows(db, p2)[0].adjustment == -4


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #


def test_idempotent_replay_decrements_once(client: TestClient, db, test_product, admin_headers):
    _stock(db, test_product, 10)
    payload = {
        "idempotency_key": "os-key-idem",
        "items": [{"product_id": test_product.id, "quantity": 4}],
    }

    r1 = client.post(_BASE, headers=admin_headers, json=payload)
    assert r1.status_code == 201, r1.text
    first_id = r1.json()["id"]

    r2 = client.post(_BASE, headers=admin_headers, json=payload)
    assert r2.status_code == 201, r2.text
    # Same order returned; stock decremented exactly once.
    assert r2.json()["id"] == first_id

    assert _qty_on_hand(db, test_product) == 6  # 10 - 4, NOT 10 - 8
    assert db.query(SalesOrder).filter(SalesOrder.external_order_id == "os-key-idem").count() == 1
    assert len(_sale_audit_rows(db, test_product)) == 1


# --------------------------------------------------------------------------- #
# Atomic rollback — the most important case
# --------------------------------------------------------------------------- #


def test_insufficient_stock_on_one_line_rolls_back_everything(
    client: TestClient, db, admin_headers
):
    ok = _product(db, price=100.0)
    short = _product(db, price=20.0)
    _stock(db, ok, 10)    # plenty
    _stock(db, short, 1)  # only 1 — the order asks for 5

    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "os-key-atomic",
            "items": [
                {"product_id": ok.id, "quantity": 2},
                {"product_id": short.id, "quantity": 5},
            ],
        },
    )

    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert body["code"] == "apiErrors.inventory.insufficientStock"

    # No order created.
    assert db.query(SalesOrder).filter(
        SalesOrder.external_order_id == "os-key-atomic"
    ).count() == 0
    # The OTHER (well-stocked) line's stock is UNCHANGED — proves the
    # earlier decrement was rolled back with the order.
    assert _qty_on_hand(db, ok) == 10
    assert _qty_on_hand(db, short) == 1
    # And no SALE audit rows survived for either product.
    assert _sale_audit_rows(db, ok) == []
    assert _sale_audit_rows(db, short) == []


# --------------------------------------------------------------------------- #
# Missing product / validation / auth
# --------------------------------------------------------------------------- #


def test_missing_product_returns_404_no_order(client: TestClient, db, admin_headers):
    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "os-key-404",
            "items": [{"product_id": 999999, "quantity": 1}],
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "apiErrors.product.notFound"
    assert db.query(SalesOrder).filter(
        SalesOrder.external_order_id == "os-key-404"
    ).count() == 0


def test_empty_items_returns_422(client: TestClient, db, admin_headers):
    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={"idempotency_key": "os-key-empty", "items": []},
    )
    assert resp.status_code == 422, resp.text


def test_non_positive_quantity_returns_422(client: TestClient, db, test_product, admin_headers):
    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "os-key-zeroqty",
            "items": [{"product_id": test_product.id, "quantity": 0}],
        },
    )
    assert resp.status_code == 422, resp.text


def test_missing_idempotency_key_returns_422(client: TestClient, db, test_product, admin_headers):
    resp = client.post(
        _BASE,
        headers=admin_headers,
        json={
            "idempotency_key": "",
            "items": [{"product_id": test_product.id, "quantity": 1}],
        },
    )
    assert resp.status_code == 422, resp.text


def test_auth_required(client: TestClient, db, test_product):
    _stock(db, test_product, 5)
    resp = client.post(
        _BASE,
        json={
            "idempotency_key": "os-key-noauth",
            "items": [{"product_id": test_product.id, "quantity": 1}],
        },
    )
    assert resp.status_code in (401, 403), resp.text
    # Nothing was created or decremented.
    assert db.query(SalesOrder).filter(
        SalesOrder.external_order_id == "os-key-noauth"
    ).count() == 0
    assert _qty_on_hand(db, test_product) == 5
