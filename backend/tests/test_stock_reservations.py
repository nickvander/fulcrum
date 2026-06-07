"""Stock reservations (OXXO/SPEI pending-payment holds).

Covers the service (reserve/consume/release/sweep) and the HTTP endpoints, plus
the order-create integration: a reservation_key consumes the hold instead of
double-decrementing, and a missing/expired key falls back to a normal decrement.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from datetime import datetime

from src.models.api_key import ApiKey
from src.models.inventory import InventoryItem, StockReservationStatus
from src.models.order import OrderSource, SalesOrder
from src.models.product import Product
from src.services import stock_reservation_service
from src.services.inventory_service import InsufficientStockError, InventoryService
from src.services.stock_reservation_service import _now

pytestmark = pytest.mark.db

service = InventoryService()


def _seed_stock(db, product, qty, *, location="default"):
    db.add(InventoryItem(product_id=product.id, quantity=qty, location=location))
    db.commit()


def _on_hand(db, product, *, location="default") -> int:
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product.id, InventoryItem.location == location)
        .first()
    )
    return int(item.quantity) if item else 0


def _make_order(db, *, key: str) -> int:
    order = SalesOrder(
        status="COMPLETED",
        total_price=10.0,
        currency="MXN",
        source=OrderSource.FULCRUM.value,
        external_order_id=key,
        created_at=datetime.utcnow(),
    )
    db.add(order)
    db.flush()
    return order.id


def _api_key_headers(db: Session, user, raw_key: str) -> dict:
    db.add(
        ApiKey(
            user_id=user.id,
            name="BFF reservation key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


# ---- service ----


def test_reserve_decrements_and_records(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    res = stock_reservation_service.reserve(
        db, reservation_key="r-1", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    assert res.status == StockReservationStatus.ACTIVE.value
    assert _on_hand(db, test_product) == 3  # 5 - 2 held
    assert len(res.items) == 1 and res.items[0].quantity == 2


def test_reserve_insufficient_raises_no_partial(db, test_product: Product):
    _seed_stock(db, test_product, 1)
    with pytest.raises(InsufficientStockError):
        stock_reservation_service.reserve(
            db, reservation_key="r-2", items=[{"product_id": test_product.id, "quantity": 5}]
        )
    # The nested SAVEPOINT already rolled back the hold; no manual rollback.
    assert _on_hand(db, test_product) == 1  # untouched
    assert stock_reservation_service.get(db, "r-2") is None


def test_reserve_idempotent(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="r-3", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    # second reserve with same key → existing hold, NO second decrement
    stock_reservation_service.reserve(
        db, reservation_key="r-3", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    assert _on_hand(db, test_product) == 3


def test_release_credits_back_and_idempotent(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="r-4", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    stock_reservation_service.release(db, "r-4")
    db.commit()
    assert _on_hand(db, test_product) == 5  # credited back
    res = stock_reservation_service.get(db, "r-4")
    assert res.status == StockReservationStatus.RELEASED.value
    # idempotent — second release does not double-credit
    stock_reservation_service.release(db, "r-4")
    db.commit()
    assert _on_hand(db, test_product) == 5


def test_consume_links_order_no_stock_change(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="r-5", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    oid = _make_order(db, key="consume-order-5")
    ok = stock_reservation_service.consume(db, "r-5", order_id=oid)
    db.commit()
    assert ok is True
    res = stock_reservation_service.get(db, "r-5")
    assert res.status == StockReservationStatus.CONSUMED.value
    assert res.order_id == oid
    assert _on_hand(db, test_product) == 3  # unchanged by consume


def test_consume_unknown_key_returns_false(db):
    assert stock_reservation_service.consume(db, "nope", order_id=1) is False


def test_release_after_consume_is_noop(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="r-6", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    oid = _make_order(db, key="consume-order-6")
    stock_reservation_service.consume(db, "r-6", order_id=oid)
    db.commit()
    stock_reservation_service.release(db, "r-6")  # consumed → no-op
    db.commit()
    assert _on_hand(db, test_product) == 3  # NOT credited back (it's a real sale)


def test_sweep_expired_releases(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db,
        reservation_key="r-7",
        items=[{"product_id": test_product.id, "quantity": 2}],
        expires_at=_now() - timedelta(seconds=1),  # already expired
    )
    db.commit()
    n = stock_reservation_service.sweep_expired(db)
    db.commit()
    assert n == 1
    assert _on_hand(db, test_product) == 5
    assert stock_reservation_service.get(db, "r-7").status == StockReservationStatus.RELEASED.value


# ---- order-create integration ----


def test_order_create_consumes_reservation(client: TestClient, db: Session, test_product, admin_headers):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="ord-res-1", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    assert _on_hand(db, test_product) == 3  # held

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "ord-with-res-1",
            "items": [{"product_id": test_product.id, "quantity": 2}],
            "reservation_key": "ord-res-1",
        },
    )
    assert resp.status_code == 201
    # Consuming the hold must NOT decrement again — still 3, not 1.
    assert _on_hand(db, test_product) == 3
    res = stock_reservation_service.get(db, "ord-res-1")
    assert res.status == StockReservationStatus.CONSUMED.value
    assert res.order_id == resp.json()["id"]


def test_order_create_without_reservation_decrements_normally(client, db, test_product, admin_headers):
    _seed_stock(db, test_product, 5)
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "ord-no-res-1",
            "items": [{"product_id": test_product.id, "quantity": 2}],
        },
    )
    assert resp.status_code == 201
    assert _on_hand(db, test_product) == 3  # normal decrement


def test_order_create_released_reservation_falls_back_to_decrement(client, db, test_product, admin_headers):
    _seed_stock(db, test_product, 5)
    stock_reservation_service.reserve(
        db, reservation_key="ord-res-rel", items=[{"product_id": test_product.id, "quantity": 2}]
    )
    db.commit()
    stock_reservation_service.release(db, "ord-res-rel")  # back to 5
    db.commit()
    assert _on_hand(db, test_product) == 5

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "ord-with-relres",
            "items": [{"product_id": test_product.id, "quantity": 2}],
            "reservation_key": "ord-res-rel",  # released → not consumed → decrements
        },
    )
    assert resp.status_code == 201
    assert _on_hand(db, test_product) == 3


# ---- endpoints ----


def test_reservation_endpoint_create_and_release(client, db, test_product, test_admin_user):
    _seed_stock(db, test_product, 5)
    headers = _api_key_headers(db, test_admin_user, "bffres-" + "a" * 57)

    create = client.post(
        "/api/v1/inventory/reservations",
        headers=headers,
        json={
            "reservation_key": "ep-1",
            "items": [{"product_id": test_product.id, "quantity": 2}],
            "expires_in_seconds": 3600,
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["status"] == "active"
    assert _on_hand(db, test_product) == 3

    rel = client.post("/api/v1/inventory/reservations/ep-1/release", headers=headers)
    assert rel.status_code == 200
    assert rel.json()["status"] == "released"
    assert _on_hand(db, test_product) == 5


def test_reservation_endpoint_insufficient_409(client, db, test_product, test_admin_user):
    _seed_stock(db, test_product, 1)
    headers = _api_key_headers(db, test_admin_user, "bffres-" + "b" * 57)
    resp = client.post(
        "/api/v1/inventory/reservations",
        headers=headers,
        json={
            "reservation_key": "ep-2",
            "items": [{"product_id": test_product.id, "quantity": 9}],
        },
    )
    assert resp.status_code == 409
    assert _on_hand(db, test_product) == 1  # untouched


def test_reservation_endpoint_requires_auth(client, db, test_product):
    _seed_stock(db, test_product, 5)
    resp = client.post(
        "/api/v1/inventory/reservations",
        json={"reservation_key": "ep-3", "items": [{"product_id": test_product.id, "quantity": 1}]},
    )
    assert resp.status_code in (401, 403)


def test_reservation_release_unknown_404(client, db, test_admin_user):
    headers = _api_key_headers(db, test_admin_user, "bffres-" + "c" * 57)
    resp = client.post("/api/v1/inventory/reservations/missing/release", headers=headers)
    assert resp.status_code == 404
