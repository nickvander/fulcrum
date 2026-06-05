"""Coverage for POST /sales-orders/{order_id}/cancel.

The storefront BFF calls this to compensate a capture failure after
order-create: cancel the order so its stock is released. The endpoint delegates
to `order_lifecycle.apply_status_change`, so it inherits the cancel-before-ship
re-credit and the `stock_recredited_at` idempotency guard.

Asserts:
  - cancel of a realized, unshipped order → status CANCELLED + stock re-credited
  - idempotent: a second cancel does NOT double-credit
  - a shipped order is cancellable but stock is NOT re-credited
  - the BFF's X-API-Key (no JWT) is accepted
  - 404 for an unknown order
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import (
    OrderSource,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatusEvent,
)
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


_SEED_COUNTER = {"n": 0}


def _seed_completed_order(db: Session, *, status: str = "COMPLETED") -> SalesOrder:
    """A realized (COMPLETED), unshipped order with one line + inventory."""
    _SEED_COUNTER["n"] += 1
    suffix = _SEED_COUNTER["n"]
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Cancel {suffix}", sku=f"CANCEL-{suffix}",
            default_resale_price=100.0, cost_price=40.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
    order = SalesOrder(
        status=status,
        total_price=200.0,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=OrderSource.FULCRUM,
        external_order_id=f"CANCEL-ORD-{suffix}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=2, price_per_unit=100.0, cost_per_unit=40.0,
    ))
    db.commit()
    db.refresh(order)
    return order


def _inventory_qty(db: Session, product_id: int) -> int:
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product_id)
        .first()
    )
    return int(item.quantity) if item else 0


def _api_key_headers(db: Session, user, raw_key: str) -> dict[str, str]:
    import hashlib

    from src.models.api_key import ApiKey

    db.add(
        ApiKey(
            user_id=user.id,
            name="BFF cancel key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


def test_cancel_recredits_stock_and_sets_status(
    client: TestClient, db, admin_headers,
):
    order = _seed_completed_order(db)
    product_id = order.items[0].product_id
    before = _inventory_qty(db, product_id)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/cancel", headers=admin_headers
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == order.id
    assert body["status"] == "CANCELLED"
    assert body["stock_recredited"] is True
    # The line's 2 units came back.
    assert _inventory_qty(db, product_id) == before + 2


def test_cancel_is_idempotent_no_double_credit(
    client: TestClient, db, admin_headers,
):
    order = _seed_completed_order(db)
    product_id = order.items[0].product_id
    before = _inventory_qty(db, product_id)

    first = client.post(
        f"/api/v1/sales-orders/{order.id}/cancel", headers=admin_headers
    )
    second = client.post(
        f"/api/v1/sales-orders/{order.id}/cancel", headers=admin_headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "CANCELLED"
    assert second.json()["stock_recredited"] is True
    # Credited exactly once despite two cancel calls.
    assert _inventory_qty(db, product_id) == before + 2


def test_cancel_shipped_order_does_not_recredit(
    client: TestClient, db, admin_headers,
):
    order = _seed_completed_order(db, status="SHIPPED")
    # Audit history must show a shipped status for the re-credit gate to block.
    db.add(SalesOrderStatusEvent(
        order_id=order.id, from_status="COMPLETED", to_status="SHIPPED",
        changed_at=datetime.utcnow(), source_signal="manual",
    ))
    db.commit()
    product_id = order.items[0].product_id
    before = _inventory_qty(db, product_id)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/cancel", headers=admin_headers
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
    assert resp.json()["stock_recredited"] is False
    # Shipped goods are not auto-credited back.
    assert _inventory_qty(db, product_id) == before


def test_cancel_with_api_key_auth(client: TestClient, db, test_admin_user):
    order = _seed_completed_order(db)
    product_id = order.items[0].product_id
    before = _inventory_qty(db, product_id)
    headers = _api_key_headers(db, test_admin_user, "bffcxl-" + "e" * 57)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/cancel", headers=headers
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"
    assert _inventory_qty(db, product_id) == before + 2


def test_cancel_without_auth_is_rejected(client: TestClient, db):
    order = _seed_completed_order(db)
    resp = client.post(f"/api/v1/sales-orders/{order.id}/cancel")
    assert resp.status_code in (401, 403)


def test_cancel_404_for_unknown_order(client: TestClient, admin_headers):
    resp = client.post(
        "/api/v1/sales-orders/9999999/cancel", headers=admin_headers
    )
    assert resp.status_code == 404
