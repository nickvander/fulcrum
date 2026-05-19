"""
Phase 8 Track 1: per-order cost engine.

Computes a per-`SalesOrder` cost breakdown — COGS + marketplace fees
+ shipping + ad spend = total cost — and writes the result into the
`order_cost_breakdowns` table. Drives the cross-channel net-margin
view the dashboard will eventually consume.

Two entrypoints:

- `upsert_breakdown(db, order)` — called from the order-ingestion
  paths (Amazon poll, ML poll, ML webhook handler) right after the
  order's line items are committed. Best-effort: caller swallows
  exceptions so a cost-engine bug never blocks an order from being
  ingested.

- `recompute_for_orders(db, *, since=..., only_missing=...)` — bulk
  recompute called by the Celery beat backfill. Catches orders
  ingested before this feature shipped + orders whose breakdown is
  stale (e.g. operator just changed `Marketplace.default_fee_rate`).

Cost-engine policy:

  - COGS: SUM(qty * COALESCE(item.cost_per_unit, product.cost_price))
    across line items. Same formula as the existing margin report so
    the gross-margin row in the new breakdown matches what operators
    already see.
  - Marketplace fees: `revenue * Marketplace.default_fee_rate`. This
    is a rough estimate — real per-order fee data comes from the
    marketplace's settlement API (ML payments + Amazon settlement
    reports), which is a follow-up. Until then this is the
    operator-configurable default. NULL marketplace (e.g. FULCRUM-
    sourced order) → 0 fees.
  - Shipping: `Marketplace.default_shipping_cost` flat per order.
    Same fallback story as fees.
  - Ad spend: 0 in v1. The marketing `Campaign` table tracks spend
    but attribution to a specific order requires more design; for
    now the field is present in the schema so the dashboard can
    surface it once attribution lands.
  - Other costs: 0 in v1. Field is open for manual adjustments
    (returns, chargebacks, etc.) once the operator workflow exists.

Currency:
  - Order's own `currency` (defaults 'MXN').
  - `exchange_rate_to_mxn` defaults to 1.0 in v1 — every order is
    MXN today. The field is wired so a future FX-aware path can
    populate it without a schema change.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace
from src.models.order import OrderCostBreakdown, OrderSource, SalesOrder


logger = logging.getLogger(__name__)


# Map `OrderSource` enum → `Marketplace.name` so we can look up the
# fee/shipping config from the source field on the order. FULCRUM is
# a non-marketplace channel (storefront-style sales), so it has no
# marketplace row to read from; fees default to 0 for it.
_SOURCE_TO_MARKETPLACE_NAME: Dict[OrderSource, str] = {
    OrderSource.AMAZON: "amazon",
    OrderSource.MERCADOLIBRE: "mercadolibre",
}


@dataclass(frozen=True)
class _CostInputs:
    """Per-order inputs the engine consumes. Built once per order, then
    handed to the pure computation function for testability."""
    revenue: float
    cogs: float
    fee_rate: float
    flat_shipping: float
    ad_spend: float
    other_cost: float


def _line_items_cogs(db: Session, order: SalesOrder) -> float:
    """Sum `qty * COALESCE(item.cost_per_unit, product.cost_price)`
    across line items. Same precedence the margin report uses, so
    legacy NULL `cost_per_unit` rows still produce a value via the
    product's current `cost_price`.

    Returns 0.0 when an order has no line items (e.g. a stub or
    refund-only record). The caller treats 0 COGS as valid input —
    a sale with no recognized cost is just full-margin in the v1
    engine.
    """
    total = 0.0
    for item in order.items or []:
        if not item or not item.quantity:
            continue
        qty = float(item.quantity)
        if item.cost_per_unit is not None:
            unit_cost = float(item.cost_per_unit)
        elif item.product is not None and item.product.cost_price is not None:
            unit_cost = float(item.product.cost_price)
        else:
            # No recognized cost basis — fall through to zero rather
            # than crashing. Surfaces as a high-margin row that the
            # operator can investigate.
            unit_cost = 0.0
        total += qty * unit_cost
    return total


def _marketplace_for_order(
    db: Session, order: SalesOrder,
) -> Optional[Marketplace]:
    """Resolve the order's `OrderSource` to a `Marketplace` row so we
    can read `default_fee_rate` / `default_shipping_cost`. Returns
    None for non-marketplace channels (FULCRUM) — caller treats that
    as "no fees, no shipping cost"."""
    if order.source is None:
        return None
    name = _SOURCE_TO_MARKETPLACE_NAME.get(order.source)
    if name is None:
        return None
    return (
        db.query(Marketplace).filter(Marketplace.name.ilike(name)).first()
    )


def _build_cost_inputs(db: Session, order: SalesOrder) -> _CostInputs:
    """Assemble the raw numbers for `compute_breakdown` from the
    order + its marketplace config."""
    revenue = float(order.total_price or 0.0)
    cogs = _line_items_cogs(db, order)
    marketplace = _marketplace_for_order(db, order)
    fee_rate = float(marketplace.default_fee_rate) if marketplace else 0.0
    flat_shipping = (
        float(marketplace.default_shipping_cost) if marketplace else 0.0
    )
    return _CostInputs(
        revenue=revenue,
        cogs=cogs,
        fee_rate=fee_rate,
        flat_shipping=flat_shipping,
        ad_spend=0.0,
        other_cost=0.0,
    )


def compute_breakdown(inputs: _CostInputs) -> Dict[str, Any]:
    """Pure computation — no DB. Returns a dict of breakdown fields
    matching the `OrderCostBreakdown` columns. Pulled out as a pure
    function so tests can exercise edge cases (zero revenue, fee
    rates > 1, etc.) without setting up an Order row.

    Capping rules:
      - `marketplace_fees_amount` is capped to >= 0. Negative fees
        don't exist; a misconfigured `default_fee_rate` shouldn't
        produce a profit boost.
      - `net_margin_percent` is None when revenue is 0 (avoid divide-
        by-zero). UI treats None as "—".
    """
    revenue = max(0.0, inputs.revenue)
    cogs = max(0.0, inputs.cogs)
    fees = max(0.0, revenue * max(0.0, inputs.fee_rate))
    shipping = max(0.0, inputs.flat_shipping)
    ads = max(0.0, inputs.ad_spend)
    other = max(0.0, inputs.other_cost)

    total_cost = cogs + fees + shipping + ads + other
    net_profit = revenue - total_cost
    net_margin_pct: Optional[float] = None
    if revenue > 0:
        net_margin_pct = (net_profit / revenue) * 100.0

    return {
        "revenue_amount": round(revenue, 4),
        "cogs_amount": round(cogs, 4),
        "marketplace_fees_amount": round(fees, 4),
        "shipping_cost_amount": round(shipping, 4),
        "ad_spend_amount": round(ads, 4),
        "other_cost_amount": round(other, 4),
        "total_cost_amount": round(total_cost, 4),
        "net_profit_amount": round(net_profit, 4),
        "net_margin_percent": (
            round(net_margin_pct, 4) if net_margin_pct is not None else None
        ),
    }


SETTLED_FEES_SOURCE = "settled"
ESTIMATED_FEES_SOURCE = "estimated"


def upsert_breakdown(
    db: Session, order: SalesOrder, *, now: Optional[datetime] = None,
) -> OrderCostBreakdown:
    """Compute the breakdown for one order and write it to the
    `order_cost_breakdowns` table (insert or update). Returns the
    persisted row.

    Caller controls the transaction — this function adds to the
    session and flushes for the unique-constraint check, but does
    NOT commit. The ingestion paths fold the breakdown into the same
    transaction as the order insert; the beat backfill commits per-
    order so one bad row doesn't roll back the whole batch.

    Safe to call repeatedly — `order_id` is uniquely constrained, so
    a recompute updates the existing row instead of stacking
    duplicates.
    """
    when = now or datetime.now(timezone.utc)
    inputs = _build_cost_inputs(db, order)
    computed = compute_breakdown(inputs)
    currency = (order.currency or "MXN").upper()
    rate = 1.0  # v1: every order is MXN; future FX work fills this
    revenue_mxn = computed["revenue_amount"] * rate

    existing = (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == order.id)
        .first()
    )
    if existing is None:
        breakdown = OrderCostBreakdown(
            order_id=order.id,
            currency=currency,
            exchange_rate_to_mxn=rate,
            revenue_amount_mxn=round(revenue_mxn, 4),
            computed_at=when,
            fees_source=ESTIMATED_FEES_SOURCE,
            **computed,
        )
        db.add(breakdown)
    else:
        existing.currency = currency
        existing.exchange_rate_to_mxn = rate
        existing.revenue_amount_mxn = round(revenue_mxn, 4)
        existing.computed_at = when
        # Preserve real settled fee data on recompute. The cost engine
        # owns COGS (which depends on local product cost), but the
        # marketplace owns marketplace_fees + shipping_cost once we've
        # ingested settlement data — a stale operator-changed fee rate
        # must not silently revert it.
        preserve_settled = existing.fees_source == SETTLED_FEES_SOURCE
        for field, value in computed.items():
            if preserve_settled and field in {
                "marketplace_fees_amount",
                "shipping_cost_amount",
            }:
                continue
            setattr(existing, field, value)
        if preserve_settled:
            # Rebuild totals/profit using the preserved settled fees,
            # not the recomputed estimates we skipped above.
            _recompute_totals_in_place(existing)
        breakdown = existing

    db.flush()
    return breakdown


def _recompute_totals_in_place(row: OrderCostBreakdown) -> None:
    """Refresh `total_cost_amount`, `net_profit_amount`, and
    `net_margin_percent` from the row's component columns. Used when
    callers overwrite individual cost components (settlement fees,
    operator adjustment) and need the rollup values to stay
    consistent without going through the full pure-compute path.
    """
    revenue = float(row.revenue_amount or 0.0)
    total = (
        float(row.cogs_amount or 0.0)
        + float(row.marketplace_fees_amount or 0.0)
        + float(row.shipping_cost_amount or 0.0)
        + float(row.ad_spend_amount or 0.0)
        + float(row.other_cost_amount or 0.0)
    )
    row.total_cost_amount = round(total, 4)
    row.net_profit_amount = round(revenue - total, 4)
    row.net_margin_percent = (
        round(((revenue - total) / revenue) * 100.0, 4) if revenue > 0 else None
    )


def apply_settlement_fees(
    db: Session,
    order: SalesOrder,
    *,
    marketplace_fees_amount: float,
    shipping_cost_amount: Optional[float] = None,
    synced_at: Optional[datetime] = None,
) -> OrderCostBreakdown:
    """Overwrite the breakdown row's fee components with real settled
    data from the marketplace's finance API and flip `fees_source` to
    'settled' so future recomputes preserve it.

    `shipping_cost_amount` is optional because some marketplaces (ML's
    `total_fee_amount`, Amazon's Commission) only carry a single fee
    bucket — in that case the caller leaves shipping untouched and the
    row keeps whatever the cost engine estimated. When it IS provided,
    it overwrites in full.

    If the breakdown row doesn't exist yet (rare — ingestion paths
    upsert one inline), we create a stub by calling `upsert_breakdown`
    first, then apply settlement on top. This keeps the settlement
    worker resilient to ingestion-time hiccups.

    Caller owns the transaction.
    """
    when = synced_at or datetime.now(timezone.utc)
    breakdown = (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == order.id)
        .first()
    )
    if breakdown is None:
        breakdown = upsert_breakdown(db, order, now=when)

    fees = max(0.0, float(marketplace_fees_amount or 0.0))
    breakdown.marketplace_fees_amount = round(fees, 4)
    if shipping_cost_amount is not None:
        breakdown.shipping_cost_amount = round(max(0.0, float(shipping_cost_amount)), 4)
    breakdown.fees_source = SETTLED_FEES_SOURCE
    breakdown.fees_synced_at = when
    breakdown.computed_at = when

    _recompute_totals_in_place(breakdown)
    db.flush()
    return breakdown


def upsert_breakdown_safe(db: Session, order: SalesOrder) -> Optional[OrderCostBreakdown]:
    """Convenience wrapper for ingestion paths: swallows exceptions
    so a cost-engine bug never blocks an order from being ingested.
    Logs to the application logger so the operator (or the beat
    backfill on the next tick) catches whatever went wrong.
    """
    try:
        return upsert_breakdown(db, order)
    except Exception:  # noqa: BLE001 — best-effort by design
        logger.exception(
            "Cost-engine upsert failed for order %s — will retry on the next beat backfill",
            order.id,
        )
        return None


# ---------------------------------------------------------------------------
# Bulk backfill
# ---------------------------------------------------------------------------


def recompute_for_orders(
    db: Session,
    *,
    since: Optional[datetime] = None,
    only_missing: bool = False,
    limit: int = 500,
) -> Dict[str, int]:
    """Bulk recompute breakdowns. Used by the Celery beat backfill
    + by tests / one-off scripts.

    `since`: when set, only orders whose `created_at >= since` are
    considered. Default None = all orders.

    `only_missing`: when True, skip orders that already have a
    breakdown row. The beat task uses this to cheaply backfill
    orders ingested before the feature shipped without re-writing
    rows the engine already produced.

    `limit`: bound on rows processed per call so one beat tick can't
    spend forever on a huge backlog.

    Returns a {breakdowns_created, breakdowns_updated, errors}
    summary so the beat task has something to log.
    """
    summary = {"breakdowns_created": 0, "breakdowns_updated": 0, "errors": 0}

    query = db.query(SalesOrder)
    if since is not None:
        query = query.filter(SalesOrder.created_at >= since)
    if only_missing:
        query = query.outerjoin(
            OrderCostBreakdown,
            OrderCostBreakdown.order_id == SalesOrder.id,
        ).filter(OrderCostBreakdown.id.is_(None))
    query = query.order_by(SalesOrder.id.asc()).limit(limit)

    orders: List[SalesOrder] = query.all()
    for order in orders:
        existed = (
            db.query(OrderCostBreakdown)
            .filter(OrderCostBreakdown.order_id == order.id)
            .first()
            is not None
        )
        try:
            upsert_breakdown(db, order)
            db.commit()
        except Exception:  # noqa: BLE001 — one bad row shouldn't kill the batch
            db.rollback()
            logger.exception(
                "Cost-engine recompute failed for order %s", order.id,
            )
            summary["errors"] += 1
            continue
        if existed:
            summary["breakdowns_updated"] += 1
        else:
            summary["breakdowns_created"] += 1
    return summary


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------


def aggregate_rollup(
    db: Session,
    *,
    window_days: int = 30,
    source: Optional[OrderSource] = None,
) -> Dict[str, Any]:
    """Aggregate breakdown over the window. Sums every numeric column
    across orders in scope + derives net margin % over the rollup
    (not the average of per-order margins, which would weight tiny
    sales the same as big ones).

    Used by `GET /api/v1/reports/cost-rollup`. Restricts to realized
    statuses so cancelled / pending orders don't pollute the headline
    margin number.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=window_days)

    query = (
        db.query(OrderCostBreakdown)
        .join(SalesOrder, SalesOrder.id == OrderCostBreakdown.order_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        # Exclude orders that were realized at some point but later got
        # cancelled/refunded. The lifecycle hook sets `reversed_at` on
        # the breakdown when the order leaves the realized set;
        # filtering on NULL keeps current-period rollups honest while
        # leaving the rows queryable by the refunds widget.
        .filter(OrderCostBreakdown.reversed_at.is_(None))
    )
    if source is not None:
        query = query.filter(SalesOrder.source == source)

    rows = query.all()
    out = {
        "orders": len(rows),
        "revenue_amount_mxn": 0.0,
        "cogs_amount": 0.0,
        "marketplace_fees_amount": 0.0,
        "shipping_cost_amount": 0.0,
        "ad_spend_amount": 0.0,
        "other_cost_amount": 0.0,
        "total_cost_amount": 0.0,
        "net_profit_amount": 0.0,
        "net_margin_percent": None,
    }
    for row in rows:
        out["revenue_amount_mxn"] += float(row.revenue_amount_mxn or 0.0)
        out["cogs_amount"] += float(row.cogs_amount or 0.0)
        out["marketplace_fees_amount"] += float(row.marketplace_fees_amount or 0.0)
        out["shipping_cost_amount"] += float(row.shipping_cost_amount or 0.0)
        out["ad_spend_amount"] += float(row.ad_spend_amount or 0.0)
        out["other_cost_amount"] += float(row.other_cost_amount or 0.0)
        out["total_cost_amount"] += float(row.total_cost_amount or 0.0)
        out["net_profit_amount"] += float(row.net_profit_amount or 0.0)

    if out["revenue_amount_mxn"] > 0:
        out["net_margin_percent"] = round(
            (out["net_profit_amount"] / out["revenue_amount_mxn"]) * 100.0, 4,
        )

    for field, value in out.items():
        if isinstance(value, float):
            out[field] = round(value, 4)
    return out


# Mirror the realized-status set the margin report uses so the
# rollup answers "what did I actually earn on completed sales?" not
# "what's the theoretical margin if every pending order closes?".
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED", "DELIVERED", "PAID")


def aggregate_rollup_by_channel(
    db: Session, *, window_days: int = 30,
) -> List[Dict[str, Any]]:
    """Per-channel rollup over the window. Returns one row per
    `OrderSource` that has at least one realized order in scope.
    Drives the dashboard's "Margin by channel" stacked bar — one
    bar per channel showing the COGS / fees / shipping / profit
    breakdown side-by-side.

    Sources with zero orders in the window are omitted (rendering
    an empty stacked bar is misleading). Ordered by revenue desc
    so the operator's eye lands on the biggest channel first.
    """
    rows: List[Dict[str, Any]] = []
    for source in OrderSource:
        rollup = aggregate_rollup(db, window_days=window_days, source=source)
        if rollup.get("orders", 0) == 0:
            continue
        rows.append({"source": source.value, **rollup})
    rows.sort(key=lambda r: r["revenue_amount_mxn"], reverse=True)
    return rows


def aggregate_daily_series(
    db: Session, *, window_days: int = 30,
) -> List[Dict[str, Any]]:
    """Daily revenue / cost / profit time-series for the dashboard's
    "Sales vs spend" line chart. Returns one row per CALENDAR DAY in
    the window — including days with zero orders (filled with zero
    values), so the chart renders a continuous line without gaps.

    Realized-status filter matches `aggregate_rollup` — pending and
    cancelled orders don't move the line.
    """
    from datetime import date, timedelta

    cutoff_date = (datetime.utcnow() - timedelta(days=window_days)).date()
    end_date = datetime.utcnow().date()

    rows = (
        db.query(OrderCostBreakdown, SalesOrder)
        .join(SalesOrder, SalesOrder.id == OrderCostBreakdown.order_id)
        .filter(SalesOrder.created_at >= datetime.combine(cutoff_date, datetime.min.time()))
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        # Same as aggregate_rollup — exclude reversed breakdowns so a
        # cancellation doesn't leave revenue on the line chart.
        .filter(OrderCostBreakdown.reversed_at.is_(None))
        .all()
    )

    by_day: Dict[date, Dict[str, float]] = {}
    for breakdown, order in rows:
        if order.created_at is None:
            continue
        day = order.created_at.date() if hasattr(order.created_at, "date") else order.created_at
        bucket = by_day.setdefault(day, {
            "revenue": 0.0, "total_cost": 0.0, "net_profit": 0.0, "orders": 0,
        })
        bucket["revenue"] += float(breakdown.revenue_amount_mxn or 0.0)
        bucket["total_cost"] += float(breakdown.total_cost_amount or 0.0)
        bucket["net_profit"] += float(breakdown.net_profit_amount or 0.0)
        bucket["orders"] += 1

    # Fill missing days so the line chart has a continuous x-axis.
    series: List[Dict[str, Any]] = []
    cursor = cutoff_date
    while cursor <= end_date:
        bucket = by_day.get(cursor, {
            "revenue": 0.0, "total_cost": 0.0, "net_profit": 0.0, "orders": 0,
        })
        series.append({
            "date": cursor.isoformat(),
            "revenue_amount_mxn": round(bucket["revenue"], 4),
            "total_cost_amount": round(bucket["total_cost"], 4),
            "net_profit_amount": round(bucket["net_profit"], 4),
            "orders": int(bucket["orders"]),
        })
        cursor = cursor + timedelta(days=1)
    return series


def top_movers(
    db: Session, *, window_days: int = 30, limit: int = 10,
) -> List[Dict[str, Any]]:
    """Top N products by revenue over the window. Each row carries
    the per-product rollup the operator needs to identify movers:
    units sold, revenue, COGS, net profit, net margin %.

    Cost basis precedence matches the gross-margin report: line
    item's `cost_per_unit` first, else current `product.cost_price`.
    Fees and shipping are NOT attributed at the product level (they
    happen at the order level), so per-product net margin reflects
    gross margin minus a pro-rata share of the order-level cost
    components. Approximation: pro-rate by revenue share.

    Returns rows ordered by revenue desc, capped at `limit`.
    """
    from datetime import timedelta
    from sqlalchemy import func as _sqlfunc

    from src.models.order import SalesOrderItem
    from src.models.product import Product

    cutoff = datetime.utcnow() - timedelta(days=window_days)

    # Step 1: per-product aggregates (units + revenue + COGS) from
    # the existing line-item table. Same SQL shape as the margin
    # report; just aggregated by product_id with COALESCE on the
    # cost basis.
    rows_raw = (
        db.query(
            SalesOrderItem.product_id,
            _sqlfunc.coalesce(_sqlfunc.sum(SalesOrderItem.quantity), 0).label("units"),
            _sqlfunc.coalesce(
                _sqlfunc.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit),
                0.0,
            ).label("revenue"),
            _sqlfunc.coalesce(
                _sqlfunc.sum(
                    SalesOrderItem.quantity
                    * _sqlfunc.coalesce(
                        SalesOrderItem.cost_per_unit, Product.cost_price,
                    )
                ),
                0.0,
            ).label("cogs"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .join(Product, Product.id == SalesOrderItem.product_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .filter(Product.is_bundle.is_(False))
        .group_by(SalesOrderItem.product_id)
        .order_by(_sqlfunc.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit).desc())
        .limit(limit)
        .all()
    )
    if not rows_raw:
        return []

    # Step 2: pro-rate the order-level fees/shipping share to each
    # product by its revenue share of the order. We pull breakdowns
    # in scope once, then compute the share factor per order.
    in_scope_orders = (
        db.query(OrderCostBreakdown, SalesOrder)
        .join(SalesOrder, SalesOrder.id == OrderCostBreakdown.order_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        # Defense in depth — the lifecycle hook only sets reversed_at
        # when the order leaves the realized set, so this should be a
        # no-op alongside the status filter, but it protects us from
        # any future path that mutates the breakdown directly.
        .filter(OrderCostBreakdown.reversed_at.is_(None))
        .all()
    )
    order_overhead_by_id: Dict[int, float] = {}
    order_revenue_by_id: Dict[int, float] = {}
    for breakdown, order in in_scope_orders:
        overhead = (
            float(breakdown.marketplace_fees_amount or 0.0)
            + float(breakdown.shipping_cost_amount or 0.0)
            + float(breakdown.ad_spend_amount or 0.0)
            + float(breakdown.other_cost_amount or 0.0)
        )
        order_overhead_by_id[order.id] = overhead
        order_revenue_by_id[order.id] = float(breakdown.revenue_amount or 0.0)

    # Per-product overhead share. For each line item in scope, take
    # its revenue share of the parent order * order overhead.
    items_in_scope = (
        db.query(
            SalesOrderItem.product_id,
            SalesOrderItem.order_id,
            SalesOrderItem.quantity,
            SalesOrderItem.price_per_unit,
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .all()
    )
    overhead_by_product: Dict[int, float] = {}
    for product_id, order_id, qty, price in items_in_scope:
        order_revenue = order_revenue_by_id.get(order_id, 0.0)
        if order_revenue <= 0:
            continue
        line_revenue = float(qty or 0) * float(price or 0.0)
        share = line_revenue / order_revenue
        overhead_by_product[product_id] = (
            overhead_by_product.get(product_id, 0.0)
            + share * order_overhead_by_id.get(order_id, 0.0)
        )

    # Step 3: fetch product names/skus for the top N.
    product_ids = [row.product_id for row in rows_raw]
    products_by_id = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }

    out: List[Dict[str, Any]] = []
    for row in rows_raw:
        revenue = float(row.revenue or 0.0)
        cogs = float(row.cogs or 0.0)
        overhead = round(overhead_by_product.get(row.product_id, 0.0), 4)
        total_cost = cogs + overhead
        net_profit = revenue - total_cost
        margin = (
            round((net_profit / revenue) * 100.0, 4) if revenue > 0 else None
        )
        product = products_by_id.get(row.product_id)
        out.append({
            "product_id": row.product_id,
            "name": product.name if product else None,
            "sku": product.sku if product else None,
            "units": int(row.units or 0),
            "revenue_amount": round(revenue, 4),
            "cogs_amount": round(cogs, 4),
            "overhead_amount": overhead,
            "total_cost_amount": round(total_cost, 4),
            "net_profit_amount": round(net_profit, 4),
            "net_margin_percent": margin,
        })
    return out
