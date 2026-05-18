"""
Coverage for `services/alert_evaluation_service.py`:

  - One test per evaluator (low_margin / sales_dip / stockout_risk):
    threshold-met vs threshold-not-met
  - Cooldown logic: triggered-but-in-cooldown → no event, no email
  - Email send: provider gets the right subject/body shape
  - Force-notify branch (the /test endpoint) bypasses cooldown
  - Batch wrapper: per-rule failure doesn't kill the loop;
    last_evaluated_at advances on every rule regardless
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from src.models.alert import AlertEvent, AlertRule, AlertType
from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.services.alert_evaluation_service import (
    evaluate_all_enabled_rules,
    evaluate_rule,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(
    db: Session, user, *, alert_type: AlertType, threshold: float,
    window_days: int = 30, cooldown_minutes: int = 720,
    notify_email: str = "alerts@example.com",
) -> AlertRule:
    rule = AlertRule(
        user_id=user.id,
        alert_type=alert_type,
        threshold=threshold,
        window_days=window_days,
        cooldown_minutes=cooldown_minutes,
        notify_email=notify_email,
        enabled=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _make_sale(
    db: Session, *, product, qty: int, price: float, cost: float | None,
    days_ago: int = 1, status: str = "COMPLETED",
):
    order = SalesOrder(
        status=status,
        total_price=qty * price,
        created_at=datetime.utcnow() - timedelta(days=days_ago),
        source=OrderSource.FULCRUM,
        external_order_id=f"TEST-{product.id}-{days_ago}-{qty}-{price}-{cost}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=price, cost_per_unit=cost,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# low_margin
# ---------------------------------------------------------------------------


def test_low_margin_triggers_when_a_product_is_below_threshold(db, test_admin_user):
    """One product at 20% margin, threshold=50% → triggered, payload
    surfaces the offender with worst-three."""
    p = Product(name="Thin Margin", sku="THIN", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0)  # margin = (10-8)/10 = 20%

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    assert result.notification_sent is True
    assert result.payload["offender_count"] == 1
    worst = result.payload["worst"]
    assert worst[0]["sku"] == "THIN"
    assert worst[0]["margin_pct"] == 20.0


def test_low_margin_does_not_trigger_when_all_above_threshold(db, test_admin_user):
    """All products at 60% margin, threshold=50% → not triggered."""
    p = Product(name="Healthy", sku="HEAL", cost_price=4.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=4.0)  # 60% margin

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        result = evaluate_rule(db, rule)
        mock_get.return_value.provider.send_email.assert_not_called()

    assert result.triggered is False


def test_low_margin_respects_window_filter(db, test_admin_user):
    """An old (out-of-window) thin-margin sale must not trigger a
    short-window rule."""
    p = Product(name="Old Thin", sku="OLD", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0, days_ago=60)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0, window_days=30)

    with patch("src.services.alert_evaluation_service.get_email_service"):
        result = evaluate_rule(db, rule)
    assert result.triggered is False


# ---------------------------------------------------------------------------
# sales_dip
# ---------------------------------------------------------------------------


def test_sales_dip_triggers_on_revenue_drop_above_threshold(db, test_admin_user):
    """Previous-window revenue $200, current-window revenue $80 → drop
    is 60% which exceeds the 50% threshold."""
    p = Product(name="Dropper", sku="DROP", cost_price=1.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    # Previous window: $200 of revenue (35 days ago, in 30-60d range).
    _make_sale(db, product=p, qty=20, price=10.0, cost=1.0, days_ago=35)
    # Current window: $80 of revenue (5 days ago).
    _make_sale(db, product=p, qty=8, price=10.0, cost=1.0, days_ago=5)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.SALES_DIP, threshold=50.0, window_days=30)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    assert result.payload["drop_pct"] == 60.0
    assert result.payload["curr_revenue"] == 80.0
    assert result.payload["prev_revenue"] == 200.0


def test_sales_dip_does_not_trigger_when_drop_below_threshold(db, test_admin_user):
    """40% drop with a 50% threshold → not triggered."""
    p = Product(name="Slight", sku="SLI", cost_price=1.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=10, price=10.0, cost=1.0, days_ago=35)
    _make_sale(db, product=p, qty=6, price=10.0, cost=1.0, days_ago=5)  # 40% drop

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.SALES_DIP, threshold=50.0, window_days=30)

    with patch("src.services.alert_evaluation_service.get_email_service"):
        result = evaluate_rule(db, rule)
    assert result.triggered is False


def test_sales_dip_does_not_trigger_when_no_baseline(db, test_admin_user):
    """No revenue in the prior window → can't compute a drop. Must
    return triggered=False with reason='no_baseline' so a brand-new
    shop doesn't get a notification storm."""
    p = Product(name="New", sku="NEW", cost_price=1.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=1, price=10.0, cost=1.0, days_ago=2)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.SALES_DIP, threshold=50.0, window_days=30)

    with patch("src.services.alert_evaluation_service.get_email_service"):
        result = evaluate_rule(db, rule)
    assert result.triggered is False
    assert result.payload["reason"] == "no_baseline"


# ---------------------------------------------------------------------------
# stockout_risk
# ---------------------------------------------------------------------------


def test_stockout_risk_triggers_when_at_risk_count_meets_threshold(db, test_admin_user):
    """Two products on hand=0 + threshold=2 → triggered. Payload
    surfaces counts and example rows."""
    p_out1 = Product(name="Out 1", sku="OUT-1", cost_price=1.0, is_bundle=False)
    p_out2 = Product(name="Out 2", sku="OUT-2", cost_price=1.0, is_bundle=False)
    db.add_all([p_out1, p_out2])
    db.flush()
    db.add_all([
        InventoryItem(product_id=p_out1.id, quantity=0, location="default"),
        InventoryItem(product_id=p_out2.id, quantity=0, location="default"),
    ])
    db.commit()

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.STOCKOUT_RISK, threshold=2.0)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    assert result.payload["at_risk_count"] == 2
    assert result.payload["out_count"] == 2
    assert result.payload["imminent_count"] == 0


def test_stockout_risk_classifies_imminent_products(db, test_admin_user):
    """5 units on hand + 30 units sold in 10d → 3/day velocity → 1.7d
    cover → imminent (<7d). Threshold=1 → triggered."""
    p = Product(name="Imm", sku="IMM", cost_price=1.0, is_bundle=False)
    db.add(p)
    db.flush()
    db.add(InventoryItem(product_id=p.id, quantity=5, location="default"))
    _make_sale(db, product=p, qty=30, price=20.0, cost=1.0, days_ago=2)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.STOCKOUT_RISK, threshold=1.0, window_days=10)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    assert result.payload["imminent_count"] == 1
    assert result.payload["out_count"] == 0


def test_stockout_risk_does_not_trigger_when_under_threshold(db, test_admin_user):
    """Only one product out — threshold of 5 not met."""
    p = Product(name="Solo Out", sku="SOLO", cost_price=1.0, is_bundle=False)
    db.add(p)
    db.flush()
    db.add(InventoryItem(product_id=p.id, quantity=0, location="default"))
    db.commit()

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.STOCKOUT_RISK, threshold=5.0)

    with patch("src.services.alert_evaluation_service.get_email_service"):
        result = evaluate_rule(db, rule)
    assert result.triggered is False


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


def test_triggered_rule_in_cooldown_does_not_send_email_or_create_event(
    db, test_admin_user
):
    """A rule that was triggered 10 minutes ago, with a 720-minute
    cooldown, must skip the notification on subsequent triggers — no
    email, no AlertEvent row. last_evaluated_at still advances."""
    p = Product(name="Thin2", sku="THIN2", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0, cooldown_minutes=720)
    rule.last_triggered_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        result = evaluate_rule(db, rule)
        mock_get.return_value.provider.send_email.assert_not_called()

    assert result.triggered is True
    assert result.notification_sent is False
    assert result.skipped_reason == "cooldown"
    assert db.query(AlertEvent).filter(AlertEvent.alert_rule_id == rule.id).count() == 0
    # last_evaluated_at must advance so an operator sees we DID check.
    # Commit so the in-session mutation is persisted and visible after
    # refresh (which re-reads from the DB).
    db.commit()
    db.refresh(rule)
    assert rule.last_evaluated_at is not None


def test_force_notify_bypasses_cooldown(db, test_admin_user):
    """The /test endpoint passes force_notify=True so the operator can
    verify the SMTP wiring even with a recent cooldown."""
    p = Product(name="Thin3", sku="THIN3", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)
    rule.last_triggered_at = datetime.now(timezone.utc)  # full cooldown
    db.commit()

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        result = evaluate_rule(db, rule, force_notify=True)
        db.commit()

    assert result.triggered is True
    assert result.notification_sent is True
    assert db.query(AlertEvent).filter(AlertEvent.alert_rule_id == rule.id).count() == 1


def test_failed_email_send_creates_event_with_error_and_does_not_advance_cooldown(
    db, test_admin_user
):
    """A SMTP send failure must:
      - record the event with notification_sent=False + error message
      - NOT advance last_triggered_at (so retry on next tick is allowed)"""
    p = Product(name="Thin4", sku="THIN4", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)
    assert rule.last_triggered_at is None

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.side_effect = RuntimeError("smtp down")
        result = evaluate_rule(db, rule)
        db.commit()

    assert result.triggered is True
    assert result.notification_sent is False
    event = db.query(AlertEvent).filter(AlertEvent.alert_rule_id == rule.id).one()
    assert event.notification_sent is False
    assert "smtp down" in (event.error or "")
    db.refresh(rule)
    assert rule.last_triggered_at is None  # still allowed to retry


# ---------------------------------------------------------------------------
# Email composition
# ---------------------------------------------------------------------------


def test_email_subject_and_body_are_alert_type_specific(db, test_admin_user):
    """The provider sees per-type subject + html with the relevant
    payload counts — verifies that the orchestrator wires through the
    right composer for each AlertType."""
    p = Product(name="Margin5", sku="M5", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=8.0)

    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        send = mock_get.return_value.provider.send_email
        send.return_value = True
        evaluate_rule(db, rule)
        kwargs = send.call_args.kwargs

    assert kwargs["to_email"] == "alerts@example.com"
    assert "below 50.0% margin" in kwargs["subject"]
    assert "M5" in kwargs["html_content"]
    assert "M5" in kwargs["text_content"]


# ---------------------------------------------------------------------------
# Batch wrapper
# ---------------------------------------------------------------------------


def test_evaluate_all_enabled_rules_runs_each_and_isolates_failures(
    db, test_admin_user
):
    """Two enabled rules. One raises inside its evaluator
    the other
    succeeds. Batch result must list both, with the failed one's
    payload carrying `error`."""
    p = Product(name="Healthy2", sku="H2", cost_price=4.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    _make_sale(db, product=p, qty=5, price=10.0, cost=4.0)

    good = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=10.0)
    bad = _make_rule(db, test_admin_user, alert_type=AlertType.SALES_DIP, threshold=50.0)

    call_count = {"n": 0}

    def _evaluator_side_effect(db_, rule_):
        call_count["n"] += 1
        if rule_.id == bad.id:
            raise RuntimeError("evaluator boom")
        from src.schemas.alert import AlertEvaluationResult
        return AlertEvaluationResult(rule_id=rule_.id, triggered=False, payload={})

    with patch.dict(
        "src.services.alert_evaluation_service._EVALUATORS",
        {AlertType.LOW_MARGIN: _evaluator_side_effect, AlertType.SALES_DIP: _evaluator_side_effect},
    ):
        batch = evaluate_all_enabled_rules(db)

    assert batch.rules_evaluated == 2
    payloads_by_rule = {r.rule_id: r.payload for r in batch.rule_results}
    assert good.id in payloads_by_rule
    assert bad.id in payloads_by_rule
    assert payloads_by_rule[bad.id]["error"] == "exception"


def test_disabled_rules_are_skipped(db, test_admin_user):
    """A disabled rule does not get evaluated."""
    rule = _make_rule(db, test_admin_user, alert_type=AlertType.LOW_MARGIN, threshold=50.0)
    rule.enabled = False
    db.commit()

    batch = evaluate_all_enabled_rules(db)
    assert batch.rules_evaluated == 0
