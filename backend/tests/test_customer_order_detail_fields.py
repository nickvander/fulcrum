"""FP-A / FP-B / FP-D — customer order detail read surface.

The storefront BFF previously papered over these gaps with a TTL-bound
checkout snapshot. These tests pin the durable contract on
``GET /api/v1/customers/me/orders/{id}``:

  * fulfillment (carrier + tracking number/url) and ``discount_amount`` are
    serialized (FP-A) — but the internal label asset URL and shipping
    internals are NOT;
  * the persisted ``ship_to`` address is serialized, and stays ``null`` for
    orders that never carried one (FP-B);
  * order lines carry ``variant_id`` (FP-D);
  * cost / supplier fields still NEVER reach the customer DTO.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import crud
from src.crud import crud_product
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product_variant import ProductVariant
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


def _seed_order(
    db: Session,
    *,
    customer_user_id: int,
    with_fulfillment: bool = False,
    with_ship_to: bool = False,
    with_variant: bool = False,
) -> SalesOrder:
    """Seed an owned FULCRUM order with one line; optionally stamp the
    fulfillment columns (as the BFF's shipping-label PUT would), a ship_to,
    and a variant on the line."""
    _SEED["n"] += 1
    suffix = _SEED["n"]
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Detail {suffix}", sku=f"DET-{suffix}",
            default_resale_price=100.0, cost_price=40.0,
        ),
    )
    variant = None
    if with_variant:
        variant = ProductVariant(
            product_id=product.id,
            name="Rojo - M",
            sku=f"DET-{suffix}-RM",
            price=110.0,
            cost_price=45.0,
        )
        db.add(variant)
        db.flush()

    order = SalesOrder(
        status="completed",
        total_price=180.0,
        discount_amount=20.0,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=OrderSource.FULCRUM.value,
        external_order_id=f"DET-ORD-{suffix}",
        customer_user_id=customer_user_id,
    )
    if with_fulfillment:
        order.shipping_carrier = "estafeta"
        order.shipping_tracking_number = "TRK123456"
        order.shipping_tracking_url = "https://track.example/TRK123456"
        order.shipping_label_url = "https://internal.example/label.pdf"
        order.shipping_label_idempotency_key = "label-key-1"
        order.shipping_cost = 99.0
    if with_ship_to:
        order.ship_to_name = "Juana Pérez"
        order.ship_to_street = "Av. Reforma 100"
        order.ship_to_colonia = "Roma Norte"
        order.ship_to_interior = "Depto 4B"
        order.ship_to_city = "Ciudad de México"
        order.ship_to_state = "CDMX"
        order.ship_to_postal_code = "06700"
        order.ship_to_country = "MX"
        order.ship_to_phone = "+52 55 1234 5678"
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id,
        product_id=product.id,
        variant_id=variant.id if variant else None,
        quantity=2,
        price_per_unit=100.0,
        cost_per_unit=40.0,
    ))
    db.commit()
    db.refresh(order)
    return order


def _get_detail(client: TestClient, headers: dict, order_id: int) -> dict:
    resp = client.get(f"/api/v1/customers/me/orders/{order_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_fulfillment_and_discount_serialized(client: TestClient, db: Session):
    """FP-A: carrier + tracking + discount_amount reach the buyer; the
    internal label URL and shipping internals do not."""
    _register(client, "detail-fa@example.com")
    headers = _customer_headers(client, db, "detail-fa@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_order(db, customer_user_id=me["id"], with_fulfillment=True)

    body = _get_detail(client, headers, order.id)
    assert body["shipping_carrier"] == "estafeta"
    assert body["shipping_tracking_number"] == "TRK123456"
    assert body["shipping_tracking_url"] == "https://track.example/TRK123456"
    assert body["discount_amount"] == pytest.approx(20.0)

    # Internal-only fulfillment fields must not leak to a customer.
    for forbidden in (
        "shipping_label_url",
        "shipping_label_idempotency_key",
        "shipping_charge_idempotency_key",
        "shipping_cost",
        "shipping_rate_id",
        "shipping_shipment_id",
    ):
        assert forbidden not in body, forbidden


def test_unshipped_order_has_null_fulfillment(client: TestClient, db: Session):
    _register(client, "detail-fa2@example.com")
    headers = _customer_headers(client, db, "detail-fa2@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_order(db, customer_user_id=me["id"])

    body = _get_detail(client, headers, order.id)
    assert body["shipping_carrier"] is None
    assert body["shipping_tracking_number"] is None
    assert body["shipping_tracking_url"] is None


def test_ship_to_serialized_when_present(client: TestClient, db: Session):
    """FP-B: the persisted ship-to address round-trips on the detail read."""
    _register(client, "detail-fb@example.com")
    headers = _customer_headers(client, db, "detail-fb@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_order(db, customer_user_id=me["id"], with_ship_to=True)

    body = _get_detail(client, headers, order.id)
    assert body["ship_to"] == {
        "name": "Juana Pérez",
        "street": "Av. Reforma 100",
        "colonia": "Roma Norte",
        "interior": "Depto 4B",
        "city": "Ciudad de México",
        "state": "CDMX",
        "postal_code": "06700",
        "country": "MX",
        "phone": "+52 55 1234 5678",
    }


def test_ship_to_null_when_absent(client: TestClient, db: Session):
    """An order without a ship-to (POS / marketplace / legacy) reads
    ``ship_to: null``, not an all-null object."""
    _register(client, "detail-fb2@example.com")
    headers = _customer_headers(client, db, "detail-fb2@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_order(db, customer_user_id=me["id"])

    body = _get_detail(client, headers, order.id)
    assert body["ship_to"] is None


def test_line_variant_id_serialized(client: TestClient, db: Session):
    """FP-D: order lines carry variant_id (null on product-level lines)."""
    _register(client, "detail-fd@example.com")
    headers = _customer_headers(client, db, "detail-fd@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    with_variant = _seed_order(db, customer_user_id=me["id"], with_variant=True)
    without_variant = _seed_order(db, customer_user_id=me["id"])

    body = _get_detail(client, headers, with_variant.id)
    line = body["items"][0]
    assert line["variant_id"] is not None
    assert line["variant_id"] == with_variant.items[0].variant_id

    body2 = _get_detail(client, headers, without_variant.id)
    assert body2["items"][0]["variant_id"] is None


def test_cost_and_supplier_fields_still_absent(client: TestClient, db: Session):
    """Defence in depth: the FP additions must not have widened the customer
    DTO to cost/supplier data."""
    _register(client, "detail-cost@example.com")
    headers = _customer_headers(client, db, "detail-cost@example.com")
    me = client.get("/api/v1/customers/me", headers=headers).json()
    order = _seed_order(
        db, customer_user_id=me["id"],
        with_fulfillment=True, with_ship_to=True, with_variant=True,
    )

    body = _get_detail(client, headers, order.id)
    flat_keys = set(body.keys())
    for item in body["items"]:
        flat_keys |= set(item.keys())
    leaked = {
        k for k in flat_keys
        if "cost" in k or "supplier" in k or "margin" in k
    }
    assert not leaked, f"cost/supplier fields leaked to customer DTO: {leaked}"
