"""Returns Phase 2 — customer self-service returns.

Covers the ownership-scoped customer endpoints and the return status lifecycle:

  - GET  /api/v1/customers/me/orders/{order_id}     (owned, cost-stripped)
  - POST /api/v1/customers/me/orders/{order_id}/returns   (request a return)
  - POST /api/v1/sales-orders/{order_id}/returns/{return_id}/transition
        (operator approval → credits stock once, lands `refunded`)

The critical security property: a customer can only see / act on orders whose
`customer_user_id` matches their JWT subject — a foreign or NULL-owner order is
a 404 (no existence oracle), and the unscoped operator endpoint is never reused.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import crud
from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import (
    OrderSource,
    SalesOrder,
    SalesOrderItem,
    SalesOrderReturn,
)
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db

_SEED = {"n": 0}


def _register(client: TestClient, email: str) -> dict:
    return client.post(
        "/api/v1/customers/register",
        json={"email": email, "password": "Password123!", "first_name": "Jane"},
    ).json()


def _customer_headers(client: TestClient, db: Session, email: str) -> dict:
    user = crud.user.get_by_email(db, email=email)
    token = crud.password_reset_token.create_reset_token(db, user_id=user.id)
    r = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _inventory_qty(db: Session, product_id: int) -> int:
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product_id)
        .first()
    )
    return int(item.quantity) if item else 0


def _seed_owned_order(
    db: Session,
    *,
    customer_user_id: int | None,
    status: str = "completed",
    created_days_ago: int = 0,
) -> SalesOrder:
    """Seed a FULCRUM order with one line item + inventory, optionally owned by
    a customer. ``created_days_ago`` ages the order for return-window tests."""
    from datetime import timedelta

    _SEED["n"] += 1
    suffix = _SEED["n"]
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Cust Ret {suffix}", sku=f"CRET-{suffix}",
            default_resale_price=50.0, cost_price=20.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
    order = SalesOrder(
        status=status,
        total_price=100.0,
        currency="MXN",
        created_at=datetime.utcnow() - timedelta(days=created_days_ago),
        source=OrderSource.FULCRUM.value,
        external_order_id=f"CRET-ORD-{suffix}",
        customer_user_id=customer_user_id,
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=2, price_per_unit=50.0, cost_per_unit=20.0,
    ))
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# GET /customers/me/orders/{id}
# ---------------------------------------------------------------------------


def test_get_my_order_returns_owned_order_cost_stripped(
    client: TestClient, db: Session,
):
    _register(client, "owner1@example.com")
    headers = _customer_headers(client, db, "owner1@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])

    resp = client.get(
        f"/api/v1/customers/me/orders/{order.id}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == order.id
    assert body["total_price"] == 100.0
    assert len(body["items"]) == 1
    # Cost / margin fields must NEVER reach the customer.
    item = body["items"][0]
    assert "cost_per_unit" not in item
    assert "net_margin_percent" not in body
    assert body["returns"] == []


def test_get_my_order_foreign_owner_is_404(client: TestClient, db: Session):
    _register(client, "ownerA@example.com")
    _register(client, "ownerB@example.com")
    headers_a = _customer_headers(client, db, "ownerA@example.com")
    me_b = _customer_headers(client, db, "ownerB@example.com")
    b_id = client.get("/api/v1/customers/me", headers=me_b).json()["id"]
    order = _seed_owned_order(db, customer_user_id=b_id)

    resp = client.get(
        f"/api/v1/customers/me/orders/{order.id}", headers=headers_a
    )
    assert resp.status_code == 404


def test_get_my_order_null_owner_is_404(client: TestClient, db: Session):
    """An operator/marketplace order (customer_user_id NULL) is invisible to the
    customer surface even though it exists."""
    _register(client, "owner2@example.com")
    headers = _customer_headers(client, db, "owner2@example.com")
    order = _seed_owned_order(db, customer_user_id=None)
    resp = client.get(
        f"/api/v1/customers/me/orders/{order.id}", headers=headers
    )
    assert resp.status_code == 404


def test_get_my_order_requires_customer_auth(client: TestClient, db: Session):
    order = _seed_owned_order(db, customer_user_id=None)
    resp = client.get(f"/api/v1/customers/me/orders/{order.id}")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /customers/me/orders/{id}/returns
# ---------------------------------------------------------------------------


def test_request_return_creates_requested_row_no_stock_movement(
    client: TestClient, db: Session,
):
    _register(client, "req1@example.com")
    headers = _customer_headers(client, db, "req1@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    qty_before = _inventory_qty(db, item.product_id)

    resp = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "reason": "defective",
            "idempotency_key": "req-key-1",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["returns"]) == 1
    ret = body["returns"][0]
    assert ret["status"] == "requested"
    # Server-derived amount = price_per_unit * qty = 50 * 1.
    assert ret["amount"] == 50.0
    # NO stock movement on a mere request.
    assert _inventory_qty(db, item.product_id) == qty_before


def test_request_return_is_idempotent(client: TestClient, db: Session):
    _register(client, "req2@example.com")
    headers = _customer_headers(client, db, "req2@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    payload = {
        "lines": [{"order_item_id": item.id, "quantity": 1}],
        "idempotency_key": "req-key-dupe",
    }
    r1 = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns", json=payload, headers=headers
    )
    r2 = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns", json=payload, headers=headers
    )
    assert r1.status_code == 201 and r2.status_code == 201
    # One logical return despite two POSTs.
    rows = db.query(SalesOrderReturn).filter(SalesOrderReturn.order_id == order.id).all()
    assert len(rows) == 1


def test_request_return_rejects_quantity_over_ordered(
    client: TestClient, db: Session,
):
    _register(client, "req3@example.com")
    headers = _customer_headers(client, db, "req3@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]  # ordered qty = 2
    resp = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 3}],
            "idempotency_key": "req-key-over",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.quantityExceedsOrdered"


def test_request_return_foreign_owner_is_404(client: TestClient, db: Session):
    _register(client, "reqX@example.com")
    _register(client, "reqY@example.com")
    headers_x = _customer_headers(client, db, "reqX@example.com")
    me_y = _customer_headers(client, db, "reqY@example.com")
    y_id = client.get("/api/v1/customers/me", headers=me_y).json()["id"]
    order = _seed_owned_order(db, customer_user_id=y_id)
    item = order.items[0]
    resp = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "req-key-foreign",
        },
        headers=headers_x,
    )
    assert resp.status_code == 404
    # And no row leaked onto the foreign order.
    assert (
        db.query(SalesOrderReturn).filter(SalesOrderReturn.order_id == order.id).count()
        == 0
    )


# ---------------------------------------------------------------------------
# Operator transition (approval) — credits stock once
# ---------------------------------------------------------------------------


def test_transition_to_refunded_credits_stock_once(
    client: TestClient, db: Session, admin_headers,
):
    _register(client, "appr1@example.com")
    headers = _customer_headers(client, db, "appr1@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    qty_before = _inventory_qty(db, item.product_id)

    created = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "appr-key-1",
        },
        headers=headers,
    ).json()
    return_id = created["returns"][0]["id"]

    # Operator approves → refunded (admin JWT is full-scope).
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded", "refund_reference": "rf_test_123"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "refunded"
    assert body["refund_reference"] == "rf_test_123"
    assert _inventory_qty(db, item.product_id) == qty_before + 1

    # Idempotent self-transition: refunded→refunded does NOT double-credit.
    resp2 = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded"},
        headers=admin_headers,
    )
    assert resp2.status_code == 200
    assert _inventory_qty(db, item.product_id) == qty_before + 1


def test_transition_rejects_invalid_jump(
    client: TestClient, db: Session, admin_headers,
):
    _register(client, "appr2@example.com")
    headers = _customer_headers(client, db, "appr2@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    created = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "appr-key-2",
        },
        headers=headers,
    ).json()
    return_id = created["returns"][0]["id"]
    # refunded → requested is not allowed.
    client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded"},
        headers=admin_headers,
    )
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "requested"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_transition_unknown_return_is_404(
    client: TestClient, db: Session, admin_headers,
):
    order = _seed_owned_order(db, customer_user_id=None)
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/9999999/transition",
        json={"status": "approved"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# customer_user_id persisted at order-create
# ---------------------------------------------------------------------------


def test_customer_jwt_cannot_reach_operator_returns_endpoints(
    client: TestClient, db: Session,
):
    """SECURITY (F1 regression): a customer SESSION JWT must NOT satisfy the
    operator/service auth (`get_current_user_with_api_key` / `require_write_scope`).
    Otherwise a customer could self-transition their own return to `refunded`
    (credit stock + stamp a refund with no real money movement) or read operator
    data. Customer self-service lives on the `/customers/me/...` surface only.
    """
    _register(client, "attacker@example.com")
    headers = _customer_headers(client, db, "attacker@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    created = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "atk-key-1",
        },
        headers=headers,
    ).json()
    return_id = created["returns"][0]["id"]
    qty_before = _inventory_qty(db, item.product_id)

    # The customer tries to self-approve via the operator transition endpoint.
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded"},
        headers=headers,
    )
    assert resp.status_code == 403
    # No stock was credited and the return stays `requested`.
    assert _inventory_qty(db, item.product_id) == qty_before

    # The customer also can't use the operator record-return or list endpoints.
    assert client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item.id, "quantity": 1}]},
        headers=headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/sales-orders/{order.id}/returns", headers=headers
    ).status_code == 403


def test_get_order_detail_accepts_api_key_and_customer_jwt(
    client: TestClient, db: Session, test_admin_user,
):
    """`GET /sales-orders/{id}` must be reachable by BOTH the storefront BFF's
    X-API-Key (server-to-server — the refund flow's authoritative order read,
    previously 401'd) AND an authenticated customer (the order-history detail).
    Regression for the latent get_order/X-API-Key gap found in live e2e."""
    import hashlib

    from src.models.api_key import ApiKey

    raw_key = "bffro-" + "e" * 58
    db.add(
        ApiKey(
            user_id=test_admin_user.id,
            name="BFF read key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    _register(client, "reader@example.com")
    headers = _customer_headers(client, db, "reader@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])

    # X-API-Key read now works (was the 401 that broke server-to-server get_order).
    r_key = client.get(
        f"/api/v1/sales-orders/{order.id}", headers={"X-API-Key": raw_key}
    )
    assert r_key.status_code == 200, r_key.text
    # Customer JWT read still works (account order-history detail path).
    assert client.get(
        f"/api/v1/sales-orders/{order.id}", headers=headers
    ).status_code == 200
    # No credentials → 401.
    assert client.get(f"/api/v1/sales-orders/{order.id}").status_code == 401


# ---------------------------------------------------------------------------
# Eligibility window + restock rules (Phase 2)
# ---------------------------------------------------------------------------


def test_request_return_rejected_outside_window(client: TestClient, db: Session):
    """A return requested past RETURN_WINDOW_DAYS (default 30) is 422."""
    _register(client, "late@example.com")
    headers = _customer_headers(client, db, "late@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"], created_days_ago=60)
    item = order.items[0]
    resp = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "late-1",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.windowExpired"
    assert (
        db.query(SalesOrderReturn).filter(SalesOrderReturn.order_id == order.id).count()
        == 0
    )


def test_request_return_rejected_for_cancelled_order(client: TestClient, db: Session):
    _register(client, "cxl@example.com")
    headers = _customer_headers(client, db, "cxl@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"], status="cancelled")
    item = order.items[0]
    resp = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "idempotency_key": "cxl-1",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.orderNotReturnable"


def test_order_detail_exposes_eligibility(client: TestClient, db: Session):
    _register(client, "elig@example.com")
    headers = _customer_headers(client, db, "elig@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()

    fresh = _seed_owned_order(db, customer_user_id=me["id"])
    d = client.get(f"/api/v1/customers/me/orders/{fresh.id}", headers=headers).json()
    assert d["returnable"] is True
    assert d["return_window_days"] == 30
    assert d["return_block_reason"] is None

    old = _seed_owned_order(db, customer_user_id=me["id"], created_days_ago=60)
    d_old = client.get(f"/api/v1/customers/me/orders/{old.id}", headers=headers).json()
    assert d_old["returnable"] is False
    assert d_old["return_block_reason"] == "window_expired"


def test_defective_return_is_not_restocked_on_approval(
    client: TestClient, db: Session, admin_headers,
):
    """A `defective` return is written off — approval refunds + lands `refunded`
    but does NOT credit sellable stock; `restock` is False on the row."""
    _register(client, "defect@example.com")
    headers = _customer_headers(client, db, "defect@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    qty_before = _inventory_qty(db, item.product_id)

    created = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "reason": "defective",
            "idempotency_key": "defect-1",
        },
        headers=headers,
    ).json()
    ret = created["returns"][0]
    assert ret["restock"] is False
    return_id = ret["id"]

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    # Defective → NOT restocked.
    assert _inventory_qty(db, item.product_id) == qty_before


def test_non_defective_return_is_restocked_on_approval(
    client: TestClient, db: Session, admin_headers,
):
    _register(client, "remorse@example.com")
    headers = _customer_headers(client, db, "remorse@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_owned_order(db, customer_user_id=me["id"])
    item = order.items[0]
    qty_before = _inventory_qty(db, item.product_id)
    created = client.post(
        f"/api/v1/customers/me/orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item.id, "quantity": 1}],
            "reason": "no_longer_needed",
            "idempotency_key": "remorse-1",
        },
        headers=headers,
    ).json()
    assert created["returns"][0]["restock"] is True
    return_id = created["returns"][0]["id"]
    client.post(
        f"/api/v1/sales-orders/{order.id}/returns/{return_id}/transition",
        json={"status": "refunded"},
        headers=admin_headers,
    )
    # Restockable → credited.
    assert _inventory_qty(db, item.product_id) == qty_before + 1


def test_create_onsite_order_persists_customer_user_id(
    db: Session, test_admin_user,
):
    from src.schemas.sales_order import SalesOrderCreate
    from src.services.order_creation import create_onsite_order

    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="OwnLink", sku="OWNLINK-1",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=5, location="default"))
    db.commit()

    payload = SalesOrderCreate(
        idempotency_key="ownlink-key-1",
        items=[{"product_id": product.id, "quantity": 1}],
        customer_user_id=test_admin_user.id,
    )
    order, created = create_onsite_order(db, payload, user_id=test_admin_user.id)
    db.commit()
    assert created is True
    assert order.customer_user_id == test_admin_user.id
