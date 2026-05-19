"""
Tests for the marketplace fee-config UI's backend:

  - PATCH /api/v1/marketplace/{id}/fee-config
  - POST  /api/v1/marketplace/{id}/recompute-cost-breakdowns

Both back the Phase-8 fee-config form so the operator can set
default_fee_rate / default_shipping_cost from the UI and refresh
existing breakdowns without a DB shell.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.marketplace import Marketplace
from src.models.order import (
    OrderCostBreakdown,
    OrderSource,
    SalesOrder,
    SalesOrderItem,
)
from src.schemas.product import ProductCreate
from src.services.order_cost_engine import upsert_breakdown


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_amazon(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://example.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


def _ensure_ml(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


def _seed_order(db, *, source, sku, total, cost) -> SalesOrder:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"FC {sku}", sku=sku,
            default_resale_price=total, cost_price=cost,
        ),
    )
    order = SalesOrder(
        status="COMPLETED", total_price=total, currency="MXN",
        created_at=datetime.utcnow(), source=source,
        external_order_id=f"FC-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=1, price_per_unit=total, cost_per_unit=cost,
    ))
    db.commit()
    return order


# ---------------------------------------------------------------------------
# PATCH /marketplace/{id}/fee-config
# ---------------------------------------------------------------------------


def test_patch_fee_config_updates_both_fields(client: TestClient, db, admin_headers):
    """Form submit with both fields filled → both persist to the
    Marketplace row, the cost engine will read them on next compute."""
    mp = _ensure_amazon(db)

    response = client.patch(
        f"/api/v1/marketplace/{mp.id}/fee-config",
        headers=admin_headers,
        json={"default_fee_rate": 0.15, "default_shipping_cost": 5.5},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["default_fee_rate"] == 0.15
    assert body["default_shipping_cost"] == 5.5

    db.refresh(mp)
    assert mp.default_fee_rate == 0.15
    assert mp.default_shipping_cost == 5.5


def test_patch_fee_config_updates_only_one_field_leaves_the_other_intact(
    client: TestClient, db, admin_headers,
):
    """Operator wants to bump fee_rate without resetting shipping —
    the PATCH body uses exclude_unset so omitted keys stay at their
    previous value."""
    mp = _ensure_amazon(db)
    mp.default_fee_rate = 0.10
    mp.default_shipping_cost = 7.5
    db.commit()

    response = client.patch(
        f"/api/v1/marketplace/{mp.id}/fee-config",
        headers=admin_headers,
        json={"default_fee_rate": 0.20},
    )
    assert response.status_code == 200
    db.refresh(mp)
    assert mp.default_fee_rate == 0.20
    assert mp.default_shipping_cost == 7.5


def test_patch_fee_config_rejects_negative_fee_rate(
    client: TestClient, db, admin_headers,
):
    """Negative fee rates would inflate net profit — a misconfigured
    value shouldn't silently pass. 400 with a localized error code
    so the form can surface the right message."""
    mp = _ensure_amazon(db)
    response = client.patch(
        f"/api/v1/marketplace/{mp.id}/fee-config",
        headers=admin_headers,
        json={"default_fee_rate": -0.1},
    )
    assert response.status_code == 400


def test_patch_fee_config_rejects_negative_shipping(
    client: TestClient, db, admin_headers,
):
    mp = _ensure_amazon(db)
    response = client.patch(
        f"/api/v1/marketplace/{mp.id}/fee-config",
        headers=admin_headers,
        json={"default_shipping_cost": -5},
    )
    assert response.status_code == 400


def test_patch_fee_config_404s_for_unknown_marketplace(
    client: TestClient, admin_headers,
):
    response = client.patch(
        "/api/v1/marketplace/99999/fee-config",
        headers=admin_headers,
        json={"default_fee_rate": 0.1},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /marketplace/{id}/recompute-cost-breakdowns
# ---------------------------------------------------------------------------


def test_recompute_after_fee_rate_change_updates_existing_breakdowns(
    client: TestClient, db, admin_headers,
):
    """After updating fee_rate, the operator clicks Recompute and
    every existing breakdown's `marketplace_fees_amount` reflects
    the new rate."""
    mp = _ensure_amazon(db)
    mp.default_fee_rate = 0.10
    mp.default_shipping_cost = 0.0
    db.commit()
    order = _seed_order(
        db, source=OrderSource.AMAZON,
        sku="RC-1", total=100.0, cost=20.0,
    )
    upsert_breakdown(db, order)
    db.commit()

    breakdown = (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == order.id)
        .one()
    )
    assert breakdown.marketplace_fees_amount == 10.0

    # Bump fee rate to 25% via the PATCH endpoint, then recompute.
    client.patch(
        f"/api/v1/marketplace/{mp.id}/fee-config",
        headers=admin_headers,
        json={"default_fee_rate": 0.25},
    )

    response = client.post(
        f"/api/v1/marketplace/{mp.id}/recompute-cost-breakdowns",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["breakdowns_updated"] == 1
    assert body["breakdowns_created"] == 0
    assert body["errors"] == 0

    db.refresh(breakdown)
    assert breakdown.marketplace_fees_amount == 25.0


def test_recompute_creates_breakdowns_for_orders_that_were_missing_one(
    client: TestClient, db, admin_headers,
):
    """Orders ingested before the cost engine landed have no
    breakdown row. The recompute endpoint must create one for each."""
    mp = _ensure_amazon(db)
    mp.default_fee_rate = 0.10
    db.commit()

    _seed_order(db, source=OrderSource.AMAZON, sku="RC-MISS-1", total=50.0, cost=10.0)
    _seed_order(db, source=OrderSource.AMAZON, sku="RC-MISS-2", total=30.0, cost=5.0)
    # Don't call upsert_breakdown; these stay un-broken-down.
    assert db.query(OrderCostBreakdown).count() == 0

    response = client.post(
        f"/api/v1/marketplace/{mp.id}/recompute-cost-breakdowns",
        headers=admin_headers,
    )
    body = response.json()
    assert body["breakdowns_created"] == 2
    assert body["breakdowns_updated"] == 0


def test_recompute_filters_by_marketplace_source(
    client: TestClient, db, admin_headers,
):
    """Recompute for Amazon only touches Amazon orders. ML orders
    stay untouched even if they're also missing breakdowns."""
    amzn = _ensure_amazon(db)
    ml = _ensure_ml(db)
    amzn.default_fee_rate = 0.15
    db.commit()

    a_order = _seed_order(db, source=OrderSource.AMAZON, sku="RC-FILT-A", total=100.0, cost=20.0)
    m_order = _seed_order(db, source=OrderSource.MERCADOLIBRE, sku="RC-FILT-M", total=80.0, cost=15.0)

    response = client.post(
        f"/api/v1/marketplace/{amzn.id}/recompute-cost-breakdowns",
        headers=admin_headers,
    )
    body = response.json()
    assert body["breakdowns_created"] == 1
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == a_order.id)
        .count() == 1
    )
    # ML order has no breakdown — wasn't recomputed because we asked
    # for Amazon only.
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == m_order.id)
        .count() == 0
    )
    # Suppress unused warning.
    assert ml.id != amzn.id


def test_recompute_returns_zeros_for_custom_marketplace_with_no_orderssource_mapping(
    client: TestClient, db, admin_headers,
):
    """A custom marketplace like "Etsy" has no OrderSource enum
    mapping, so it can't have any orders to recompute. Endpoint
    returns 0s instead of a 5xx."""
    custom = Marketplace(name="Etsy", api_base_url="https://example.com")
    db.add(custom)
    db.commit()

    response = client.post(
        f"/api/v1/marketplace/{custom.id}/recompute-cost-breakdowns",
        headers=admin_headers,
    )
    body = response.json()
    assert body == {"breakdowns_created": 0, "breakdowns_updated": 0, "errors": 0}


def test_recompute_404s_for_unknown_marketplace(
    client: TestClient, admin_headers,
):
    response = client.post(
        "/api/v1/marketplace/99999/recompute-cost-breakdowns",
        headers=admin_headers,
    )
    assert response.status_code == 404
