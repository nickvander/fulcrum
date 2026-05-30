"""Coverage for the ml_full_stockout_risk alert evaluator.

A SKU is "at risk" when it sells on MercadoLibre but its Full stock
(on-hand at location 'ml-full' + in-transit transfers to Full) won't
cover ML demand over the Full replenishment horizon. Velocity is scoped
to ML orders — Amazon/internal sales don't draw down Full stock.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from src.models.alert import AlertRule, AlertType
from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.models.stock_transfer import (
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.services.alert_evaluation_service import (
    _evaluate_ml_full_stockout_risk,
    evaluate_rule,
)


pytestmark = pytest.mark.db

_N = {"i": 0}


def _product(db: Session) -> Product:
    _N["i"] += 1
    p = Product(
        name=f"Full SKU {_N['i']}", sku=f"FULL-{_N['i']}",
        cost_price=50.0, default_resale_price=120.0, is_bundle=False,
    )
    db.add(p)
    db.flush()
    return p


def _rule(db, user, *, threshold: float, window_days: int = 30) -> AlertRule:
    rule = AlertRule(
        user_id=user.id, alert_type=AlertType.ML_FULL_STOCKOUT_RISK,
        threshold=threshold, window_days=window_days, cooldown_minutes=720,
        notify_email="ops@example.com", enabled=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _ml_sale(db, *, product, qty: int, days_ago: int = 1, source=OrderSource.MERCADOLIBRE):
    _N["i"] += 1
    o = SalesOrder(
        status="COMPLETED", total_price=qty * 120.0,
        created_at=datetime.utcnow() - timedelta(days=days_ago),
        source=source, external_order_id=f"MLF-{_N['i']}",
    )
    db.add(o)
    db.flush()
    db.add(SalesOrderItem(order_id=o.id, product_id=product.id, quantity=qty, price_per_unit=120.0))
    db.commit()


def _full_stock(db, *, product, qty: int):
    db.add(InventoryItem(product_id=product.id, quantity=qty, location=LOCATION_ML_FULL))
    db.commit()


def _transfer_to_full(db, *, product, qty_shipped: int, qty_received: int = 0,
                      status=StockTransferStatus.SHIPPED):
    t = StockTransfer(source_location="internal", dest_location=LOCATION_ML_FULL, status=status.value)
    db.add(t)
    db.flush()
    db.add(StockTransferItem(
        transfer_id=t.id, product_id=product.id,
        qty_planned=qty_shipped, qty_shipped=qty_shipped, qty_received=qty_received,
    ))
    db.commit()


# --------------------------------------------------------------------------- #
# Evaluator
# --------------------------------------------------------------------------- #


def test_out_bucket_ml_velocity_but_no_full_stock(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=30)  # 1/day over 30d
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is True
    assert result.payload["out_count"] == 1
    assert result.payload["at_risk_count"] == 1
    assert result.payload["out_examples"][0]["sku"] == p.sku


def test_imminent_bucket_low_full_cover(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=60)        # 2/day
    _full_stock(db, product=p, qty=10)     # 10 / 2 = 5 days cover <= 14 horizon
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is True
    assert result.payload["imminent_count"] == 1
    assert result.payload["out_count"] == 0
    ex = result.payload["imminent_examples"][0]
    assert ex["days_of_cover"] == pytest.approx(5.0)


def test_in_transit_transfer_suppresses_risk(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=30)              # 1/day
    # No on-hand, but 60 units shipped to Full → 60 days cover > 14 horizon.
    _transfer_to_full(db, product=p, qty_shipped=60)
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is False
    assert result.payload["at_risk_count"] == 0


def test_partially_received_transfer_counts_remaining_in_transit(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=30)  # 1/day
    # 60 shipped, 58 received → 2 still in transit; no on-hand → 2 days cover <= 14.
    _transfer_to_full(db, product=p, qty_shipped=60, qty_received=58,
                      status=StockTransferStatus.PARTIALLY_RECEIVED)
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is True
    assert result.payload["imminent_count"] == 1


def test_non_ml_sales_do_not_count(db, test_admin_user):
    p = _product(db)
    # Sells on Amazon + internal, never ML; zero Full stock.
    _ml_sale(db, product=p, qty=50, source=OrderSource.AMAZON)
    _ml_sale(db, product=p, qty=50, source=OrderSource.FULCRUM)
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is False
    assert result.payload["at_risk_count"] == 0


def test_healthy_full_cover_not_at_risk(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=30)       # 1/day
    _full_stock(db, product=p, qty=100)   # 100 days cover > 14
    rule = _rule(db, test_admin_user, threshold=1)

    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.triggered is False


def test_threshold_gates_count(db, test_admin_user):
    p1, p2 = _product(db), _product(db)
    _ml_sale(db, product=p1, qty=30)
    _ml_sale(db, product=p2, qty=30)
    # 2 SKUs out; threshold=3 → not triggered.
    rule = _rule(db, test_admin_user, threshold=3)
    result = _evaluate_ml_full_stockout_risk(db, rule)
    assert result.payload["at_risk_count"] == 2
    assert result.triggered is False


# --------------------------------------------------------------------------- #
# Wiring: dispatch table + email composition (force_notify path)
# --------------------------------------------------------------------------- #


def test_evaluate_rule_dispatches_and_composes_email(db, test_admin_user):
    p = _product(db)
    _ml_sale(db, product=p, qty=30)
    rule = _rule(db, test_admin_user, threshold=1)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule, force_notify=True)

    assert result.triggered is True
    # Email was composed + sent through the provider without error.
    mock_get.return_value.provider.send_email.assert_called_once()
    _args, kwargs = mock_get.return_value.provider.send_email.call_args
    blob = f"{kwargs}".lower()
    assert "full" in blob  # Full-specific subject/body, not the generic stockout copy
