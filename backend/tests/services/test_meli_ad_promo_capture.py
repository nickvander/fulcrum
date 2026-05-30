"""B2 — MELI promotions / Product-Ads cost capture.

  - The ML settlement parser splits fee_details into marketplace /
    advertising / promotion buckets (no double-counting).
  - apply_settlement_fees writes ad_spend_amount + other_cost_amount and
    recomputes net margin, so ad spend stops being an assumed zero.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.order import OrderCostBreakdown, OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate
from src.services import order_cost_engine
from src.services.marketplaces.mercadolibre import (
    MercadoLibreConnector,
    _classify_fee_detail,
)


pytestmark = pytest.mark.db

_N = {"i": 0}


# --------------------------------------------------------------------------- #
# Parser (pure)
# --------------------------------------------------------------------------- #


def test_classify_fee_detail_buckets():
    assert _classify_fee_detail({"type": "mercadopago_fee"}) == "marketplace"
    assert _classify_fee_detail({"type": "advertising_fee"}) == "advertising"
    assert _classify_fee_detail({"name": "Product Ads"}) == "advertising"
    assert _classify_fee_detail({"type": "promotion", "name": "Hot Sale deal"}) == "promotion"
    assert _classify_fee_detail({"description": "descuento de campaña"}) == "promotion"
    assert _classify_fee_detail({}) == "marketplace"


def test_extract_splits_fee_buckets_without_double_counting():
    payload = {
        "payments": [
            {
                "status": "approved",
                "fee_details": [
                    {"type": "mercadopago_fee", "amount": 30.0},
                    {"type": "advertising_fee", "amount": 12.0},
                    {"type": "promotion", "amount": 8.0},
                ],
            }
        ],
        "shipping": {"shipping_cost": 50.0},
    }
    out = MercadoLibreConnector._extract_settlement_from_order(payload)
    assert out["marketplace_fees_amount"] == pytest.approx(30.0)  # ads/promo excluded
    assert out["ad_spend_amount"] == pytest.approx(12.0)
    assert out["other_cost_amount"] == pytest.approx(8.0)
    assert out["shipping_cost_amount"] == pytest.approx(50.0)


def test_extract_top_level_advertising_fallback():
    payload = {
        "payments": [{"status": "approved", "marketplace_fee": 25.0}],
        "advertising_fee": 9.0,
    }
    out = MercadoLibreConnector._extract_settlement_from_order(payload)
    assert out["marketplace_fees_amount"] == pytest.approx(25.0)
    assert out["ad_spend_amount"] == pytest.approx(9.0)
    assert out["other_cost_amount"] is None  # nothing promotion-like


def test_extract_no_ads_or_promo_leaves_them_none():
    payload = {"payments": [{"status": "approved", "marketplace_fee": 10.0}]}
    out = MercadoLibreConnector._extract_settlement_from_order(payload)
    assert out["ad_spend_amount"] is None
    assert out["other_cost_amount"] is None


# --------------------------------------------------------------------------- #
# Cost-engine routing
# --------------------------------------------------------------------------- #


def _ml_order(db: Session, *, price: float, cost: float, qty: int = 1) -> SalesOrder:
    _N["i"] += 1
    o = SalesOrder(
        status="COMPLETED", total_price=price * qty, currency="MXN",
        created_at=datetime.utcnow(), source=OrderSource.MERCADOLIBRE,
        external_order_id=f"ADPROMO-{_N['i']}",
    )
    db.add(o)
    db.flush()
    p = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name=f"AdPromo {_N['i']}", sku=f"ADP-{_N['i']}",
                             default_resale_price=price, cost_price=cost),
    )
    db.add(SalesOrderItem(order_id=o.id, product_id=p.id, quantity=qty,
                          price_per_unit=price, cost_per_unit=cost))
    db.commit()
    db.refresh(o)
    return o


def test_apply_settlement_writes_ad_spend_and_promo_into_net(db):
    o = _ml_order(db, price=200.0, cost=80.0)  # revenue 200, cogs 80
    order_cost_engine.upsert_breakdown(db, o)
    db.commit()

    order_cost_engine.apply_settlement_fees(
        db, o,
        marketplace_fees_amount=20.0,
        shipping_cost_amount=10.0,
        ad_spend_amount=15.0,
        other_cost_amount=5.0,
    )
    db.commit()
    cb = db.query(OrderCostBreakdown).filter(OrderCostBreakdown.order_id == o.id).first()
    assert cb.ad_spend_amount == pytest.approx(15.0)
    assert cb.other_cost_amount == pytest.approx(5.0)
    # net = 200 - (80 cogs + 20 fees + 10 shipping + 15 ads + 5 other) = 70
    assert cb.net_profit_amount == pytest.approx(70.0)
    assert cb.fees_source == "settled"


def test_apply_settlement_none_leaves_ad_spend_untouched(db):
    o = _ml_order(db, price=100.0, cost=40.0)
    order_cost_engine.upsert_breakdown(db, o)
    db.commit()
    # No ad/promo passed → those components stay at their estimated 0,
    # not overwritten with garbage.
    order_cost_engine.apply_settlement_fees(db, o, marketplace_fees_amount=8.0)
    db.commit()
    cb = db.query(OrderCostBreakdown).filter(OrderCostBreakdown.order_id == o.id).first()
    assert cb.ad_spend_amount == pytest.approx(0.0)
    assert cb.other_cost_amount == pytest.approx(0.0)
    assert cb.marketplace_fees_amount == pytest.approx(8.0)
