"""Coverage for the sales-order returns workflow:

  - POST /sales-orders/{order_id}/returns
  - GET  /sales-orders/{order_id}/returns
  - Service-layer validation branches
  - Side effect: each returned line credits stock via
    `inventory_service.adjust_stock` with `reason_code='return'`
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


_SEED_COUNTER = {"n": 0}


def _seed_order_with_two_items(db: Session) -> SalesOrder:
    """Helper: seeds a paid order with two line items + inventory
    rows so we can assert on the stock side after returns. Each
    invocation uses a fresh SKU suffix so the helper is safe to call
    multiple times in one test (e.g. when comparing two orders)."""
    _SEED_COUNTER["n"] += 1
    suffix = _SEED_COUNTER["n"]
    p_a = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Ret A {suffix}", sku=f"RET-A-{suffix}",
            default_resale_price=50.0, cost_price=20.0,
        ),
    )
    p_b = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Ret B {suffix}", sku=f"RET-B-{suffix}",
            default_resale_price=80.0, cost_price=30.0,
        ),
    )
    db.add_all([
        InventoryItem(product_id=p_a.id, quantity=10, location="default"),
        InventoryItem(product_id=p_b.id, quantity=10, location="default"),
    ])
    order = SalesOrder(
        status="PAID",
        total_price=210.0,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=OrderSource.MERCADOLIBRE,
        external_order_id=f"RET-ORDER-{suffix}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=p_a.id,
        quantity=2, price_per_unit=50.0, cost_per_unit=20.0,
    ))
    db.add(SalesOrderItem(
        order_id=order.id, product_id=p_b.id,
        quantity=1, price_per_unit=80.0, cost_per_unit=30.0,
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


# ---------------------------------------------------------------------------
# POST /sales-orders/{order_id}/returns
# ---------------------------------------------------------------------------


def test_record_return_credits_stock_and_persists_row(
    client: TestClient, db, admin_headers,
):
    """Happy path: one item returned → stock credited + return row +
    audit row with reason_code='return'."""
    order = _seed_order_with_two_items(db)
    item_a, item_b = order.items
    starting_qty_a = _inventory_qty(db, item_a.product_id)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={
            "lines": [{"order_item_id": item_a.id, "quantity": 1}],
            "reason": "Buyer changed mind",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["order_id"] == order.id
    assert rows[0]["order_item_id"] == item_a.id
    # Service falls back to the item's product_id when the caller
    # didn't pin one — confirm that worked.
    assert rows[0]["product_id"] == item_a.product_id
    assert rows[0]["quantity"] == 1
    assert rows[0]["reason"] == "Buyer changed mind"

    # Stock credited.
    assert _inventory_qty(db, item_a.product_id) == starting_qty_a + 1

    # Audit row carries the return reason_code.
    adj = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.product_id == item_a.product_id)
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )
    assert adj is not None
    assert adj.reason_code == "return"
    assert adj.adjustment == 1


def test_record_return_supports_multiple_lines_at_once(
    client: TestClient, db, admin_headers,
):
    """A multi-line return (2-of-3 SKUs back) is one POST creating
    two return rows. Both line items get their stock credited
    independently."""
    order = _seed_order_with_two_items(db)
    item_a, item_b = order.items
    qa_before = _inventory_qty(db, item_a.product_id)
    qb_before = _inventory_qty(db, item_b.product_id)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={
            "lines": [
                {"order_item_id": item_a.id, "quantity": 2},
                {"order_item_id": item_b.id, "quantity": 1},
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert len(resp.json()) == 2
    assert _inventory_qty(db, item_a.product_id) == qa_before + 2
    assert _inventory_qty(db, item_b.product_id) == qb_before + 1


def test_record_return_rejects_empty_lines(
    client: TestClient, db, admin_headers,
):
    order = _seed_order_with_two_items(db)
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [], "reason": "nope"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.noLines"


def test_record_return_rejects_zero_quantity(
    client: TestClient, db, admin_headers,
):
    order = _seed_order_with_two_items(db)
    item_a = order.items[0]
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item_a.id, "quantity": 0}]},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.quantityMustBePositive"


def test_record_return_rejects_item_from_different_order(
    client: TestClient, db, admin_headers,
):
    """Defensive: the operator's UI shouldn't send this, but if
    something cross-references items the API must refuse."""
    order_a = _seed_order_with_two_items(db)
    # A second order whose items belong to a different order.
    order_b = _seed_order_with_two_items(db)
    item_in_b = order_b.items[0]

    resp = client.post(
        f"/api/v1/sales-orders/{order_a.id}/returns",
        json={"lines": [{"order_item_id": item_in_b.id, "quantity": 1}]},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.salesOrderReturn.itemNotInOrder"


def test_record_return_404_for_unknown_order(
    client: TestClient, admin_headers,
):
    resp = client.post(
        "/api/v1/sales-orders/9999999/returns",
        json={"lines": [{"product_id": 1, "quantity": 1}]},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_record_return_accepts_product_id_only_for_legacy_orders(
    client: TestClient, db, admin_headers, test_admin_user,
):
    """Legacy orders may have line items where product_id is None
    (we couldn't map at ingestion time). The operator can still
    record a return by passing product_id directly."""
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="Legacy", sku="LEGACY-1",
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=5, location="default"))
    order = SalesOrder(
        status="PAID", total_price=10.0, currency="MXN",
        created_at=datetime.utcnow(), source=OrderSource.MERCADOLIBRE,
        external_order_id="LEGACY-ORD",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(  # No product mapping
        order_id=order.id, product_id=None,
        quantity=1, price_per_unit=10.0, cost_per_unit=None,
    ))
    db.commit()
    db.refresh(order)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"product_id": product.id, "quantity": 1}]},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert _inventory_qty(db, product.id) == 6


def test_record_return_with_api_key_auth(
    client: TestClient, db, test_admin_user,
):
    """The storefront BFF records returns server-to-server with an X-API-Key
    (no JWT). The returns endpoint accepts it via `get_current_user_with_api_key`
    (mirrors order-create FP-04), so the BFF's refund→return flow can re-credit
    stock without an operator session. Regression for the auth gap that would
    otherwise 403 the BFF call."""
    import hashlib

    from src.models.api_key import ApiKey

    raw_key = "bffret-" + "c" * 57  # long, deterministic; prefix = raw_key[:8]
    db.add(
        ApiKey(
            user_id=test_admin_user.id,
            name="BFF returns key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    order = _seed_order_with_two_items(db)
    item_a = order.items[0]
    qa_before = _inventory_qty(db, item_a.product_id)

    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        headers={"X-API-Key": raw_key},  # no Authorization/JWT
        json={"lines": [{"order_item_id": item_a.id, "quantity": 1}], "reason": "defective"},
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()[0]["order_id"] == order.id
    # Stock credited via the API-key call — the BFF server-to-server path works.
    assert _inventory_qty(db, item_a.product_id) == qa_before + 1
    # The recorder is the API key's owning user.
    assert resp.json()[0]["recorded_by_user_id"] == test_admin_user.id


def test_record_return_without_auth_is_rejected(client: TestClient, db):
    """No JWT and no X-API-Key → rejected (the endpoint is not public)."""
    order = _seed_order_with_two_items(db)
    item_a = order.items[0]
    resp = client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item_a.id, "quantity": 1}]},
    )
    assert resp.status_code in (401, 403)


def test_list_returns_with_api_key_auth(
    client: TestClient, db, test_admin_user,
):
    """The BFF can also read returns back with an X-API-Key."""
    import hashlib

    from src.models.api_key import ApiKey

    raw_key = "bffretl-" + "d" * 56
    db.add(
        ApiKey(
            user_id=test_admin_user.id,
            name="BFF returns list key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    order = _seed_order_with_two_items(db)
    resp = client.get(
        f"/api/v1/sales-orders/{order.id}/returns",
        headers={"X-API-Key": raw_key},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /sales-orders/{order_id}/returns
# ---------------------------------------------------------------------------


def test_list_returns_returns_recorded_rows_newest_first(
    client: TestClient, db, admin_headers,
):
    order = _seed_order_with_two_items(db)
    item_a = order.items[0]

    # Two POSTs → two return rows. The most recent one lands at index 0.
    client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item_a.id, "quantity": 1}], "reason": "first"},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item_a.id, "quantity": 1}], "reason": "second"},
        headers=admin_headers,
    )

    resp = client.get(
        f"/api/v1/sales-orders/{order.id}/returns",
        headers=admin_headers,
    )
    body = resp.json()
    assert resp.status_code == 200
    assert len(body) == 2
    assert body[0]["reason"] == "second"
    assert body[1]["reason"] == "first"
    # Recorder's email is filled in for the admin-headers actor.
    assert body[0]["recorded_by_email"] == "admin@test.com"


def test_list_returns_empty_when_none_recorded(
    client: TestClient, db, admin_headers,
):
    order = _seed_order_with_two_items(db)
    resp = client.get(
        f"/api/v1/sales-orders/{order.id}/returns",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_404_for_unknown_order(
    client: TestClient, admin_headers,
):
    resp = client.get(
        "/api/v1/sales-orders/9999999/returns",
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Side effect: audit-page filter on reason_code='return' finds them
# ---------------------------------------------------------------------------


def test_returns_show_up_in_audit_log_filtered_by_return_reason(
    client: TestClient, db, admin_headers,
):
    """End-to-end: record a return, then hit the audit endpoint with
    `reason_code=return` and confirm the stock credit row is in the
    result. This is the operator's workflow for "show me everything
    that came back this month"."""
    order = _seed_order_with_two_items(db)
    item_a = order.items[0]
    client.post(
        f"/api/v1/sales-orders/{order.id}/returns",
        json={"lines": [{"order_item_id": item_a.id, "quantity": 1}], "reason": "buyer remorse"},
        headers=admin_headers,
    )

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"reason_code": "return"},
        headers=admin_headers,
    )
    body = resp.json()
    matched = [r for r in body["rows"] if r["product_id"] == item_a.product_id]
    assert len(matched) >= 1
    assert matched[0]["adjustment"] == 1
    assert matched[0]["reason_code"] == "return"
