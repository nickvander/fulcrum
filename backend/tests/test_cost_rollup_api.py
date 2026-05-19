"""
End-to-end test for `GET /api/v1/reports/cost-rollup`.

The endpoint is the one Track 2's dashboard will consume to render
the net-margin headline. Tests focus on the HTTP contract — the
underlying math is covered by
`tests/services/test_order_cost_engine.py`.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.marketplace import Marketplace
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate
from src.services.order_cost_engine import upsert_breakdown


pytestmark = pytest.mark.db


def _ensure_amazon(db):
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.15
    mp.default_shipping_cost = 5.0
    db.commit()
    db.refresh(mp)
    return mp


def _ensure_ml(db):
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.16
    db.commit()
    db.refresh(mp)
    return mp


def _seed_order(db, *, source, total, sku, qty, price, cost, status="COMPLETED"):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Rollup {sku}", sku=sku,
            default_resale_price=price, cost_price=cost,
        ),
    )
    order = SalesOrder(
        status=status, total_price=total, currency="MXN",
        created_at=datetime.utcnow(), source=source,
        external_order_id=f"EXT-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=price, cost_per_unit=cost,
    ))
    db.commit()
    upsert_breakdown(db, order)
    db.commit()
    return order


def test_cost_rollup_aggregates_across_channels(
    client: TestClient, db, admin_headers,
):
    """A mixed-channel window returns one rolled-up row with the
    blended margin number. Operator opens the dashboard and sees
    one headline figure that's the truth across all sales."""
    _ensure_amazon(db)
    _ensure_ml(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=300.0, sku="ROLLUP-A", qty=1, price=300.0, cost=60.0,
    )
    _seed_order(
        db, source=OrderSource.MERCADOLIBRE,
        total=200.0, sku="ROLLUP-M", qty=1, price=200.0, cost=40.0,
    )

    response = client.get(
        "/api/v1/reports/cost-rollup?window_days=30", headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["orders"] == 2
    assert body["window_days"] == 30
    assert body["source"] is None
    assert body["revenue_amount_mxn"] == 500.0
    assert body["cogs_amount"] == 100.0
    # Margin is a real number, not None — we have revenue.
    assert body["net_margin_percent"] is not None


def test_cost_rollup_filters_by_source(
    client: TestClient, db, admin_headers,
):
    """`source=amazon` returns only Amazon orders, mirroring the
    aggregate_rollup behavior covered in the service-level tests."""
    _ensure_amazon(db)
    _ensure_ml(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, sku="RP-API-AMZN", qty=1, price=100.0, cost=20.0,
    )
    _seed_order(
        db, source=OrderSource.MERCADOLIBRE,
        total=200.0, sku="RP-API-ML", qty=1, price=200.0, cost=40.0,
    )

    response = client.get(
        "/api/v1/reports/cost-rollup?window_days=30&source=amazon",
        headers=admin_headers,
    )
    body = response.json()
    assert body["orders"] == 1
    assert body["source"] == "AMAZON"
    assert body["revenue_amount_mxn"] == 100.0


def test_cost_rollup_rejects_unknown_source(
    client: TestClient, db, admin_headers,
):
    """A typo like `?source=etsy` returns 400 with a localized error
    code, not a silent empty rollup."""
    response = client.get(
        "/api/v1/reports/cost-rollup?source=etsy", headers=admin_headers,
    )
    assert response.status_code == 400


def test_cost_rollup_empty_window_returns_zeros(
    client: TestClient, db, admin_headers,
):
    """No orders → orders=0, revenue=0, margin=null. UI must
    handle this without rendering NaN/Infinity."""
    response = client.get(
        "/api/v1/reports/cost-rollup?window_days=1", headers=admin_headers,
    )
    body = response.json()
    assert body["orders"] == 0
    assert body["revenue_amount_mxn"] == 0.0
    assert body["net_margin_percent"] is None


def test_cost_rollup_requires_auth(client: TestClient):
    response = client.get("/api/v1/reports/cost-rollup")
    assert response.status_code == 401
