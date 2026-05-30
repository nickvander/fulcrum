"""Coverage for the enriched order-detail endpoint + FX-aware cost engine.

  - GET /sales-orders/{id} now returns the cost/fee/margin breakdown,
    the status timeline, Amazon refund events, and per-line cost.
  - order_cost_engine.upsert_breakdown normalizes revenue to MXN using
    the FX rate recorded for the order date.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.order import (
    AmazonOrderRefund,
    OrderSource,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatusEvent,
)
from src.schemas.product import ProductCreate
from src.services import currency_service, order_cost_engine


pytestmark = pytest.mark.db

_N = {"i": 0}


def _product(db: Session, *, cost: float, price: float, currency: str = "MXN"):
    _N["i"] += 1
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"OD {_N['i']}", sku=f"OD-{_N['i']}",
            cost_price=cost, default_resale_price=price, currency=currency,
        ),
    )


def _order(db: Session, *, source, currency, product, qty, price, when=None):
    o = SalesOrder(
        status="COMPLETED", total_price=qty * price, currency=currency,
        created_at=when or datetime.utcnow(), source=source,
        external_order_id=f"OD-{_N['i']}-{source}",
    )
    db.add(o)
    db.flush()
    db.add(SalesOrderItem(order_id=o.id, product_id=product.id, quantity=qty,
                          price_per_unit=price, cost_per_unit=product.cost_price))
    db.flush()
    db.refresh(o)
    order_cost_engine.upsert_breakdown(db, o)
    db.commit()
    db.refresh(o)
    return o


# --------------------------------------------------------------------------- #
# Enriched detail endpoint
# --------------------------------------------------------------------------- #


def test_detail_includes_cost_breakdown_and_per_line_cost(client: TestClient, db, admin_headers):
    p = _product(db, cost=80.0, price=200.0)
    o = _order(db, source=OrderSource.MERCADOLIBRE, currency="MXN", product=p, qty=2, price=200.0)

    resp = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Per-line cost surfaces for margin math.
    assert body["items"][0]["cost_per_unit"] == 80.0

    cb = body["cost_breakdown"]
    assert cb is not None
    assert cb["revenue_amount"] == pytest.approx(400.0)      # 2 × 200
    assert cb["cogs_amount"] == pytest.approx(160.0)         # 2 × 80
    assert cb["net_profit_amount"] == pytest.approx(240.0)   # no fees configured
    assert cb["fees_source"] == "estimated"
    assert cb["currency"] == "MXN"


def test_detail_includes_status_timeline(client: TestClient, db, admin_headers):
    p = _product(db, cost=10.0, price=25.0)
    o = _order(db, source=OrderSource.AMAZON, currency="MXN", product=p, qty=1, price=25.0)
    db.add(SalesOrderStatusEvent(
        order_id=o.id, from_status=None, to_status="PAID",
        changed_at=datetime.now(timezone.utc), source_signal="amazon_poll",
    ))
    db.add(SalesOrderStatusEvent(
        order_id=o.id, from_status="PAID", to_status="SHIPPED",
        changed_at=datetime.now(timezone.utc) + timedelta(minutes=5), source_signal="amazon_poll",
    ))
    db.commit()

    body = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers).json()
    tl = body["status_timeline"]
    assert [e["to_status"] for e in tl] == ["PAID", "SHIPPED"]  # oldest → newest
    assert tl[0]["from_status"] is None


def test_detail_includes_amazon_refund_events(client: TestClient, db, admin_headers):
    p = _product(db, cost=10.0, price=25.0)
    o = _order(db, source=OrderSource.AMAZON, currency="MXN", product=p, qty=3, price=25.0)
    db.add(AmazonOrderRefund(
        order_id=o.id, amazon_refund_id="RF-1", posted_at=datetime.now(timezone.utc),
        refund_amount=25.0, currency="MXN",
    ))
    db.commit()

    body = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers).json()
    assert len(body["refund_events"]) == 1
    assert body["refund_events"][0]["refund_id"] == "RF-1"
    assert body["refund_events"][0]["refund_amount"] == pytest.approx(25.0)


def test_detail_breakdown_absent_is_null(client: TestClient, db, admin_headers):
    # An order with no breakdown row → cost_breakdown null, empty lists.
    o = SalesOrder(status="PENDING", total_price=0.0, currency="MXN",
                   created_at=datetime.utcnow(), source=OrderSource.FULCRUM,
                   external_order_id="OD-NOBREAKDOWN")
    db.add(o)
    db.commit()
    db.refresh(o)
    body = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers).json()
    assert body["cost_breakdown"] is None
    assert body["status_timeline"] == []
    assert body["refund_events"] == []


# --------------------------------------------------------------------------- #
# FX-aware cost engine
# --------------------------------------------------------------------------- #


def test_cost_engine_uses_historical_fx_for_usd_order(client: TestClient, db, admin_headers):
    # Record a USD→MXN rate that was true on/before the order date.
    currency_service.record_rate(
        db, base_currency="USD", quote_currency="MXN", rate=18.0, rate_date=date(2026, 3, 1),
    )
    db.commit()

    p = _product(db, cost=5.0, price=20.0, currency="USD")
    o = _order(
        db, source=OrderSource.AMAZON, currency="USD", product=p, qty=2, price=20.0,
        when=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
    )

    body = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers).json()
    cb = body["cost_breakdown"]
    # Native revenue is US$40; MXN-normalized at 18.0 = MX$720.
    assert cb["currency"] == "USD"
    assert cb["revenue_amount"] == pytest.approx(40.0)
    assert cb["exchange_rate_to_mxn"] == pytest.approx(18.0)
    assert cb["revenue_amount_mxn"] == pytest.approx(720.0)


def test_cost_engine_mxn_order_rate_is_identity(client: TestClient, db, admin_headers):
    p = _product(db, cost=80.0, price=200.0, currency="MXN")
    o = _order(db, source=OrderSource.MERCADOLIBRE, currency="MXN", product=p, qty=1, price=200.0)
    cb = client.get(f"/api/v1/sales-orders/{o.id}", headers=admin_headers).json()["cost_breakdown"]
    assert cb["exchange_rate_to_mxn"] == 1.0
    assert cb["revenue_amount_mxn"] == pytest.approx(cb["revenue_amount"])
