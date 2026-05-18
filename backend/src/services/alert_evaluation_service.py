"""
Alert evaluation. Reads `AlertRule`s, runs the appropriate evaluator
against the same SQL helpers powering the velocity/margin/stockout
reports, and routes triggered rules to the email channel (subject to
the per-rule cooldown).

Three evaluators, one per `AlertType`. Each returns
`AlertEvaluationResult(triggered, payload)`; the orchestrator handles
event-row creation, cooldown logic, and the email send.

Email body composition is intentionally simple — these are operator
nudges, not customer-facing emails. The HTML body links to the
relevant dashboard widget so the operator can click through.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.alert import AlertEvent, AlertRule, AlertType
from src.models.inventory import InventoryItem
from src.models.order import SalesOrder, SalesOrderItem
from src.models.product import Product
from src.schemas.alert import (
    AlertEvaluationBatchResult,
    AlertEvaluationResult,
)
from src.services.email_service import get_email_service


logger = logging.getLogger(__name__)


# Status values that count as realized sales. Mirrors the margin /
# velocity reports' filter so an alert and a manual export agree on
# what counts.
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED")


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------


def _evaluate_low_margin(db: Session, rule: AlertRule) -> AlertEvaluationResult:
    """Trigger when ANY product's gross-margin % over the window is
    below `rule.threshold`. Payload includes the count of offending
    products and the worst-three (lowest-margin) for the email body.

    Margin formula matches `_build_margin_rows`:
      revenue = SUM(qty * price_per_unit)
      cost    = SUM(qty * COALESCE(items.cost_per_unit, products.cost_price))
      margin_pct = (revenue - cost) / revenue * 100
    """
    cutoff = datetime.utcnow() - timedelta(days=rule.window_days)
    rows = (
        db.query(
            SalesOrderItem.product_id,
            Product.name,
            Product.sku,
            func.coalesce(func.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit), 0.0),
            func.coalesce(
                func.sum(
                    SalesOrderItem.quantity
                    * func.coalesce(SalesOrderItem.cost_per_unit, Product.cost_price)
                ),
                0.0,
            ),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .join(Product, Product.id == SalesOrderItem.product_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .filter(Product.is_bundle.is_(False))
        .group_by(SalesOrderItem.product_id, Product.name, Product.sku)
        .all()
    )

    offenders = []
    for pid, name, sku, revenue, cost in rows:
        revenue_f = float(revenue or 0.0)
        if revenue_f <= 0:
            continue
        cost_f = float(cost or 0.0)
        margin_pct = (revenue_f - cost_f) / revenue_f * 100.0
        if margin_pct < rule.threshold:
            offenders.append({
                "product_id": pid,
                "name": name,
                "sku": sku,
                "revenue": round(revenue_f, 2),
                "cost": round(cost_f, 2),
                "margin_pct": round(margin_pct, 2),
            })

    offenders.sort(key=lambda r: r["margin_pct"])  # worst first
    triggered = len(offenders) > 0
    payload = {
        "offender_count": len(offenders),
        "threshold": rule.threshold,
        "window_days": rule.window_days,
        "worst": offenders[:3],
    }
    return AlertEvaluationResult(rule_id=rule.id, triggered=triggered, payload=payload)


def _evaluate_sales_dip(db: Session, rule: AlertRule) -> AlertEvaluationResult:
    """Trigger when total realized revenue in the most-recent
    `window_days` dropped by >= `rule.threshold` percent vs the
    *previous* window of the same length.

    `drop_pct = (prev - curr) / prev * 100`. A negative value (sales
    went UP) never triggers.

    Skipped (not triggered, payload notes the reason) when prev_window
    revenue is zero — there's no baseline to compare against, and we
    don't want a new-shop notification storm.
    """
    now = datetime.utcnow()
    curr_start = now - timedelta(days=rule.window_days)
    prev_start = curr_start - timedelta(days=rule.window_days)

    def _revenue(start: datetime, end: datetime) -> float:
        result = (
            db.query(
                func.coalesce(
                    func.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit),
                    0.0,
                )
            )
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
            .filter(SalesOrder.created_at >= start)
            .filter(SalesOrder.created_at < end)
            .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
            .scalar()
        )
        return float(result or 0.0)

    curr_revenue = _revenue(curr_start, now)
    prev_revenue = _revenue(prev_start, curr_start)

    if prev_revenue <= 0:
        return AlertEvaluationResult(
            rule_id=rule.id, triggered=False,
            payload={
                "reason": "no_baseline",
                "curr_revenue": round(curr_revenue, 2),
                "prev_revenue": 0.0,
                "window_days": rule.window_days,
            },
        )

    drop_pct = (prev_revenue - curr_revenue) / prev_revenue * 100.0
    triggered = drop_pct >= rule.threshold
    return AlertEvaluationResult(
        rule_id=rule.id,
        triggered=triggered,
        payload={
            "drop_pct": round(drop_pct, 2),
            "threshold": rule.threshold,
            "curr_revenue": round(curr_revenue, 2),
            "prev_revenue": round(prev_revenue, 2),
            "window_days": rule.window_days,
        },
    )


def _evaluate_stockout_risk(db: Session, rule: AlertRule) -> AlertEvaluationResult:
    """Trigger when the number of products in the "out" (on_hand == 0)
    or "imminent" (days_of_inventory < 7) buckets is >= rule.threshold.

    Mirrors `_build_stockout_rows`'s logic but skips the watch tier
    (operators don't want hourly emails about "watch" products that
    are still ~14 days out).
    """
    cutoff = datetime.utcnow() - timedelta(days=rule.window_days)
    sales_rows = (
        db.query(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .group_by(SalesOrderItem.product_id)
        .all()
    )
    sales = {pid: int(units or 0) for pid, units in sales_rows}

    on_hand_rows = (
        db.query(
            InventoryItem.product_id,
            func.coalesce(func.sum(InventoryItem.quantity), 0),
        )
        .group_by(InventoryItem.product_id)
        .all()
    )
    on_hand_map = {pid: int(qty or 0) for pid, qty in on_hand_rows}

    products = (
        db.query(Product)
        .filter(Product.is_bundle.is_(False))
        .order_by(Product.id.asc())
        .limit(2000)
        .all()
    )

    out: list[Dict[str, Any]] = []
    imminent: list[Dict[str, Any]] = []
    for product in products:
        on_hand = on_hand_map.get(product.id, 0)
        units = sales.get(product.id, 0)
        velocity = units / rule.window_days if rule.window_days else 0.0

        if on_hand <= 0:
            out.append({"product_id": product.id, "sku": product.sku, "name": product.name})
            continue
        if velocity <= 0:
            continue
        days_left = round(on_hand / velocity, 1)
        if days_left <= 7:
            imminent.append({
                "product_id": product.id, "sku": product.sku, "name": product.name,
                "on_hand": on_hand, "days_of_inventory": days_left,
            })

    total = len(out) + len(imminent)
    triggered = total >= rule.threshold
    return AlertEvaluationResult(
        rule_id=rule.id,
        triggered=triggered,
        payload={
            "at_risk_count": total,
            "out_count": len(out),
            "imminent_count": len(imminent),
            "threshold": rule.threshold,
            "out_examples": out[:3],
            "imminent_examples": imminent[:3],
        },
    )


_EVALUATORS = {
    AlertType.LOW_MARGIN: _evaluate_low_margin,
    AlertType.SALES_DIP: _evaluate_sales_dip,
    AlertType.STOCKOUT_RISK: _evaluate_stockout_risk,
}


# ---------------------------------------------------------------------------
# Email composition
# ---------------------------------------------------------------------------


def _email_subject(rule: AlertRule, payload: Dict[str, Any]) -> str:
    if rule.alert_type == AlertType.LOW_MARGIN:
        return f"Fulcrum alert: {payload.get('offender_count', '?')} products below {rule.threshold:.1f}% margin"
    if rule.alert_type == AlertType.SALES_DIP:
        return f"Fulcrum alert: sales dropped {payload.get('drop_pct', 0):.1f}% over {rule.window_days}d"
    return f"Fulcrum alert: {payload.get('at_risk_count', '?')} products at stockout risk"


def _email_body(rule: AlertRule, payload: Dict[str, Any]) -> tuple[str, str]:
    """Returns (html, text). Keep both compact — these are operator
    nudges, not full reports. Link points at the dashboard
    `/dashboard` so the operator can deep-link into the corresponding
    widget."""
    if rule.alert_type == AlertType.LOW_MARGIN:
        worst = payload.get("worst") or []
        rows_html = "".join(
            f"<li>{r['name']} ({r['sku']}): {r['margin_pct']:.1f}% margin on ${r['revenue']:,.2f} revenue</li>"
            for r in worst
        )
        body_html = (
            f"<p>{payload.get('offender_count', 0)} products are below your "
            f"{rule.threshold:.1f}% margin threshold over the last "
            f"{rule.window_days} days.</p>"
            f"<ul>{rows_html}</ul>"
            f"<p>Open the <a href='/dashboard'>margin report</a> for the full list.</p>"
        )
        rows_text = "\n".join(
            f"- {r['name']} ({r['sku']}): {r['margin_pct']:.1f}% margin on ${r['revenue']:,.2f}"
            for r in worst
        )
        body_text = (
            f"{payload.get('offender_count', 0)} products below "
            f"{rule.threshold:.1f}% margin over {rule.window_days}d.\n\n{rows_text}"
        )
        return body_html, body_text

    if rule.alert_type == AlertType.SALES_DIP:
        body_html = (
            f"<p>Revenue dropped <strong>{payload.get('drop_pct', 0):.1f}%</strong> "
            f"over the last {rule.window_days} days "
            f"(current ${payload.get('curr_revenue', 0):,.2f} vs previous "
            f"${payload.get('prev_revenue', 0):,.2f}).</p>"
            f"<p>Open the <a href='/dashboard'>sales-by-channel widget</a> "
            f"to see which channels drove the drop.</p>"
        )
        body_text = (
            f"Revenue dropped {payload.get('drop_pct', 0):.1f}% over "
            f"{rule.window_days}d (current ${payload.get('curr_revenue', 0):,.2f} "
            f"vs previous ${payload.get('prev_revenue', 0):,.2f})."
        )
        return body_html, body_text

    # stockout_risk
    out_examples = payload.get("out_examples") or []
    imm_examples = payload.get("imminent_examples") or []
    out_html = "".join(f"<li>{r['name']} ({r['sku']})</li>" for r in out_examples)
    imm_html = "".join(
        f"<li>{r['name']} ({r['sku']}): {r['days_of_inventory']:.1f}d left</li>"
        for r in imm_examples
    )
    body_html = (
        f"<p>{payload.get('at_risk_count', 0)} products at stockout risk: "
        f"{payload.get('out_count', 0)} already out, "
        f"{payload.get('imminent_count', 0)} with &lt;7 days cover.</p>"
        f"<h4>Out of stock</h4><ul>{out_html or '<li>None</li>'}</ul>"
        f"<h4>Imminent</h4><ul>{imm_html or '<li>None</li>'}</ul>"
        f"<p>Open the <a href='/dashboard'>stockout report</a> for the full list.</p>"
    )
    out_text = "\n".join(f"- {r['name']} ({r['sku']})" for r in out_examples) or "(none)"
    imm_text = "\n".join(
        f"- {r['name']} ({r['sku']}): {r['days_of_inventory']:.1f}d left"
        for r in imm_examples
    ) or "(none)"
    body_text = (
        f"{payload.get('at_risk_count', 0)} products at risk "
        f"({payload.get('out_count', 0)} out, "
        f"{payload.get('imminent_count', 0)} imminent).\n\n"
        f"Out of stock:\n{out_text}\n\nImminent:\n{imm_text}"
    )
    return body_html, body_text


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _in_cooldown(rule: AlertRule, now: datetime) -> bool:
    if rule.last_triggered_at is None:
        return False
    elapsed = now - rule.last_triggered_at
    return elapsed.total_seconds() < rule.cooldown_minutes * 60


def evaluate_rule(
    db: Session,
    rule: AlertRule,
    *,
    now: Optional[datetime] = None,
    force_notify: bool = False,
) -> AlertEvaluationResult:
    """Run one evaluation. On a triggered + uncooldowned result:
      - Compose + send the email
      - Insert an AlertEvent row (notification_sent reflects send outcome)
      - Advance `last_triggered_at` on a successful send so cooldown starts

    `last_evaluated_at` is always bumped.

    `force_notify=True` bypasses the cooldown — used by the
    /alerts/rules/{id}/test endpoint so an operator can verify the
    setup without waiting for the cooldown to expire.
    """
    now = now or datetime.now(timezone.utc)

    evaluator = _EVALUATORS.get(AlertType(rule.alert_type))
    if evaluator is None:
        rule.last_evaluated_at = now
        return AlertEvaluationResult(
            rule_id=rule.id, triggered=False, payload={"reason": "unknown_alert_type"},
        )

    result = evaluator(db, rule)
    rule.last_evaluated_at = now

    if not result.triggered:
        return result

    if not force_notify and _in_cooldown(rule, now):
        result.skipped_reason = "cooldown"
        return result

    # Send the email
    subject = _email_subject(rule, result.payload)
    html, text = _email_body(rule, result.payload)
    sent = False
    error: Optional[str] = None
    try:
        sent = bool(get_email_service().provider.send_email(
            to_email=rule.notify_email,
            subject=subject,
            html_content=html,
            text_content=text,
        ))
    except Exception as exc:  # noqa: BLE001 — log and surface in the event row
        logger.exception("Alert email send failed for rule %d", rule.id)
        error = str(exc)[:500]

    db.add(AlertEvent(
        alert_rule_id=rule.id,
        triggered_at=now,
        payload=result.payload,
        notification_sent=sent,
        error=error,
    ))
    result.notification_sent = sent
    if sent:
        rule.last_triggered_at = now
    return result


def evaluate_all_enabled_rules(
    db: Session, *, now: Optional[datetime] = None,
) -> AlertEvaluationBatchResult:
    """Run every enabled rule. Per-rule failures are caught + logged
    so one bad rule (e.g. a bug in an evaluator hitting bad data)
    doesn't kill the whole sweep. Commits per-rule for the same
    reason."""
    from src.crud.crud_alert import alert_rule as crud_alert_rule

    now = now or datetime.now(timezone.utc)
    rules = crud_alert_rule.list_enabled(db)

    rule_results = []
    notifications_sent = 0
    triggered_count = 0
    for rule in rules:
        sp = db.begin_nested()
        try:
            result = evaluate_rule(db, rule, now=now)
            sp.commit()
            db.commit()
            rule_results.append(result)
            if result.triggered:
                triggered_count += 1
            if result.notification_sent:
                notifications_sent += 1
        except Exception:  # noqa: BLE001 — keep the sweep alive
            sp.rollback()
            logger.exception("Alert evaluation failed for rule %d", rule.id)
            rule_results.append(AlertEvaluationResult(
                rule_id=rule.id, triggered=False,
                payload={"error": "exception"},
            ))

    return AlertEvaluationBatchResult(
        rules_evaluated=len(rules),
        rules_triggered=triggered_count,
        notifications_sent=notifications_sent,
        rule_results=rule_results,
    )
