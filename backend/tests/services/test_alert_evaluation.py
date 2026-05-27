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


# ---------------------------------------------------------------------------
# Refund-rate-spike evaluator
# ---------------------------------------------------------------------------


def _seed_realized_orders_with_refunds(
    db: Session, *, total_orders: int, refunded: int,
) -> None:
    """Helper: seeds `total_orders` realized ML orders; flips
    `refunded` of them out of the realized set so the evaluator
    sees a refund_rate."""
    from src.services.order_lifecycle import apply_status_change, record_initial_status
    from src.services import order_cost_engine
    from src.crud import crud_product
    from src.schemas.product import ProductCreate

    orders: list[SalesOrder] = []
    for i in range(total_orders):
        product = crud_product.product.create(
            db=db,
            obj_in=ProductCreate(
                name=f"RA-{i}", sku=f"RA-{i}",
                default_resale_price=100.0, cost_price=40.0,
            ),
        )
        db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
        order = SalesOrder(
            status="PAID",
            total_price=100.0,
            currency="MXN",
            created_at=datetime.utcnow(),
            source=OrderSource.MERCADOLIBRE,
            external_order_id=f"RA-{i}",
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            order_id=order.id, product_id=product.id,
            quantity=1, price_per_unit=100.0, cost_per_unit=40.0,
        ))
        db.commit()
        db.refresh(order)
        order_cost_engine.upsert_breakdown(db, order)
        record_initial_status(db, order, source_signal="ml_poll")
        db.commit()
        orders.append(order)

    for order in orders[:refunded]:
        apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()


def test_refund_rate_evaluator_triggers_above_threshold(db, test_admin_user):
    """4 ML orders seeded; 2 get cancelled. After cancellation only
    2 orders are still realized in the window (cancelled ones drop
    out), so refunds/realized = 2/2 = 100%. A 20% threshold fires;
    a 250% threshold doesn't (intentionally above the 100% ceiling
    so we exercise the under-threshold branch)."""
    _seed_realized_orders_with_refunds(db, total_orders=4, refunded=2)

    fires = _make_rule(
        db, test_admin_user, alert_type=AlertType.REFUND_RATE_SPIKE,
        threshold=20.0,
    )
    quiet = _make_rule(
        db, test_admin_user, alert_type=AlertType.REFUND_RATE_SPIKE,
        threshold=250.0,
    )

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        fires_result = evaluate_rule(db, fires)
        quiet_result = evaluate_rule(db, quiet)

    assert fires_result.triggered is True
    assert fires_result.payload["refund_rate_percent"] == pytest.approx(100.0)
    assert quiet_result.triggered is False


def test_refund_rate_evaluator_zero_denominator_does_not_fire(db, test_admin_user):
    """No realized orders in the window — rate is None, never triggers."""
    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.REFUND_RATE_SPIKE,
        threshold=1.0,
    )
    result = evaluate_rule(db, rule)
    assert result.triggered is False
    assert result.payload["realized_orders_count"] == 0


def test_refund_rate_evaluator_below_threshold_does_not_fire(db, test_admin_user):
    """1 refund out of 10 realized = 10% rate. Threshold 25% → quiet."""
    _seed_realized_orders_with_refunds(db, total_orders=10, refunded=1)
    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.REFUND_RATE_SPIKE,
        threshold=25.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)
    assert result.triggered is False
    # 1 refund / 9 still-realized = ~11.11%
    assert result.payload["refund_rate_percent"] == pytest.approx(11.11)


# ---------------------------------------------------------------------------
# Settlement-variance evaluator
# ---------------------------------------------------------------------------


def _seed_settled_orders(
    db: Session,
    *,
    marketplace_name: str,
    default_fee_rate: float,
    orders: list[tuple[float, float]],  # [(revenue, actual_fee), ...]
) -> None:
    """Seed `Marketplace.default_fee_rate` + N settled orders with
    the supplied actual fee amounts. Used by the settlement-variance
    evaluator tests."""
    from src.models.marketplace import Marketplace
    from src.models.order import OrderCostBreakdown, OrderSource
    from src.services import order_cost_engine
    from src.services.order_lifecycle import record_initial_status
    from datetime import datetime as _dt

    source = (
        OrderSource.MERCADOLIBRE
        if marketplace_name.lower() == "mercadolibre"
        else OrderSource.AMAZON
    )

    mp = db.query(Marketplace).filter(Marketplace.name.ilike(marketplace_name)).first()
    if mp is None:
        mp = Marketplace(name=marketplace_name, api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = default_fee_rate
    db.commit()

    for i, (revenue, actual_fee) in enumerate(orders):
        order = SalesOrder(
            status="PAID",
            total_price=revenue,
            currency="MXN",
            created_at=_dt.utcnow(),
            source=source,
            external_order_id=f"VAR-{marketplace_name}-{i}",
        )
        db.add(order)
        db.flush()
        db.add(SalesOrderItem(
            order_id=order.id, product_id=None,
            quantity=1, price_per_unit=revenue, cost_per_unit=0.0,
        ))
        db.commit()
        db.refresh(order)
        order_cost_engine.upsert_breakdown(db, order)
        # Flip to settled with the supplied actual fee.
        order_cost_engine.apply_settlement_fees(
            db, order,
            marketplace_fees_amount=actual_fee,
        )
        record_initial_status(db, order, source_signal="ml_poll")
        db.commit()
        # Manually pin the breakdown's reversed_at to None just in
        # case (apply_settlement_fees leaves it alone, but make the
        # invariant explicit).
        breakdown = (
            db.query(OrderCostBreakdown)
            .filter(OrderCostBreakdown.order_id == order.id)
            .first()
        )
        assert breakdown.reversed_at is None
        assert breakdown.fees_source == "settled"


def test_settlement_variance_fires_when_actual_above_expected(db, test_admin_user):
    """Marketplace default_fee_rate = 10% but Amazon actually charged
    15% across the window → variance ≈ +50%. Threshold 25% → fires."""
    _seed_settled_orders(
        db, marketplace_name="Amazon", default_fee_rate=0.10,
        orders=[(100.0, 15.0), (100.0, 15.0), (100.0, 15.0)],
    )

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=25.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    amzn = next(m for m in result.payload["marketplaces"] if m["source"] == "AMAZON")
    assert amzn["orders"] == 3
    assert amzn["actual_fees_amount"] == pytest.approx(45.0)
    assert amzn["expected_fees_amount"] == pytest.approx(30.0)
    assert amzn["variance_percent"] == pytest.approx(50.0)


def test_settlement_variance_fires_when_actual_below_expected(db, test_admin_user):
    """Below-expected variance (promo deduction, marketplace-funded
    discount) also fires — operator wants the signal in both
    directions. abs(variance) is what's compared to the threshold."""
    _seed_settled_orders(
        db, marketplace_name="MercadoLibre", default_fee_rate=0.16,
        orders=[(100.0, 8.0)],  # expected 16, actual 8 → -50%
    )

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=25.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    ml = next(m for m in result.payload["marketplaces"] if m["source"] == "MERCADOLIBRE")
    assert ml["variance_percent"] == pytest.approx(-50.0)


def test_settlement_variance_quiet_when_within_threshold(db, test_admin_user):
    """5% variance with a 10% threshold → quiet. Real-world fees
    won't match estimates exactly; the threshold absorbs noise."""
    _seed_settled_orders(
        db, marketplace_name="Amazon", default_fee_rate=0.10,
        orders=[(100.0, 10.5)],  # 5% high
    )

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=10.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is False
    amzn = next(m for m in result.payload["marketplaces"] if m["source"] == "AMAZON")
    assert amzn["variance_percent"] == pytest.approx(5.0)


def test_settlement_variance_skips_marketplaces_without_rate(db, test_admin_user):
    """A marketplace with `default_fee_rate=0` has no prediction —
    the evaluator skips it instead of dividing by zero. Other
    marketplaces with rates configured still drive the alert."""
    _seed_settled_orders(
        db, marketplace_name="Amazon", default_fee_rate=0.0,
        orders=[(100.0, 20.0)],  # would be "infinite" variance
    )
    _seed_settled_orders(
        db, marketplace_name="MercadoLibre", default_fee_rate=0.10,
        orders=[(100.0, 20.0)],  # +100% variance
    )

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=25.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    assert result.triggered is True
    sources = {m["source"] for m in result.payload["marketplaces"]}
    # Amazon (rate=0) skipped; MercadoLibre present.
    assert "AMAZON" not in sources
    assert "MERCADOLIBRE" in sources


def test_settlement_variance_skips_estimated_orders(db, test_admin_user):
    """Orders still in `fees_source='estimated'` MUST NOT enter the
    calculation — they tautologically match the predicted rate (that
    rate is literally how they were generated). Only settled orders
    drive the alert."""
    from src.models.marketplace import Marketplace
    from src.models.order import OrderSource
    from src.services import order_cost_engine

    mp = Marketplace(name="Amazon", api_base_url="x", default_fee_rate=0.10)
    db.add(mp)
    db.flush()
    db.commit()

    # One estimated order; cost engine fills marketplace_fees_amount
    # at 10% by default — but the evaluator should still report no
    # in-scope orders for Amazon.
    order = SalesOrder(
        status="PAID", total_price=100.0, currency="MXN",
        created_at=datetime.utcnow(), source=OrderSource.AMAZON,
        external_order_id="EST-1",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=None,
        quantity=1, price_per_unit=100.0, cost_per_unit=0.0,
    ))
    db.commit()
    db.refresh(order)
    order_cost_engine.upsert_breakdown(db, order)
    db.commit()

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=25.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    # Estimated orders excluded → Amazon row absent (orders=0 was
    # the skip path).
    sources = {m["source"] for m in result.payload["marketplaces"]}
    assert "AMAZON" not in sources
    assert result.triggered is False


def test_settlement_variance_skips_reversed_orders(db, test_admin_user):
    """Reversed (cancelled-after-settlement) orders fall out of the
    rollup so a cancellation doesn't pollute the variance signal."""
    from src.services.order_lifecycle import apply_status_change

    _seed_settled_orders(
        db, marketplace_name="Amazon", default_fee_rate=0.10,
        orders=[(100.0, 20.0)],  # would be +100% variance
    )
    # Flip the single seeded order's status to CANCELLED — that
    # toggles reversed_at on its breakdown.
    only_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.source == OrderSource.AMAZON)
        .first()
    )
    apply_status_change(db, only_order, new_status="cancelled", source_signal="amazon_poll")
    db.commit()

    rule = _make_rule(
        db, test_admin_user, alert_type=AlertType.SETTLEMENT_VARIANCE,
        threshold=10.0,
    )
    with patch("src.services.alert_evaluation_service.get_email_service") as mock_email:
        mock_email.return_value.send_email.return_value = True
        result = evaluate_rule(db, rule)

    sources = {m["source"] for m in result.payload["marketplaces"]}
    assert "AMAZON" not in sources
    assert result.triggered is False
