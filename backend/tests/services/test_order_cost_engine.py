"""
Coverage for `services/order_cost_engine.py` — the Phase 8 Track 1
cost engine.

Three layers tested:

  1. Pure `compute_breakdown` — edge cases on the math (zero revenue,
     misconfigured fee rates, no line items, etc.) without setting
     up a SalesOrder row.
  2. `upsert_breakdown` against a real DB — inserts the breakdown
     row, updates existing rows idempotently, reads marketplace fee
     config correctly.
  3. `recompute_for_orders` bulk runner — `only_missing` filter,
     per-order isolation (one bad row doesn't kill the batch),
     `since` cursor.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
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
from src.services.order_cost_engine import (
    _CostInputs,
    aggregate_rollup,
    compute_breakdown,
    recompute_for_orders,
    upsert_breakdown,
    upsert_breakdown_safe,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Pure computation
# ---------------------------------------------------------------------------


def test_compute_breakdown_simple_happy_path():
    """Revenue 100, COGS 40, fee 10%, shipping 3 → fees 10, total
    cost 53, profit 47, margin 47%."""
    result = compute_breakdown(_CostInputs(
        revenue=100.0, cogs=40.0, fee_rate=0.10,
        flat_shipping=3.0, ad_spend=0.0, other_cost=0.0,
    ))
    assert result["revenue_amount"] == 100.0
    assert result["cogs_amount"] == 40.0
    assert result["marketplace_fees_amount"] == 10.0
    assert result["shipping_cost_amount"] == 3.0
    assert result["total_cost_amount"] == 53.0
    assert result["net_profit_amount"] == 47.0
    assert result["net_margin_percent"] == 47.0


def test_compute_breakdown_zero_revenue_returns_null_margin():
    """A zero-revenue row (refunds, cancellations) returns
    `net_margin_percent=None` — diving by zero would lie. UI renders
    None as '—' instead of '0%'."""
    result = compute_breakdown(_CostInputs(
        revenue=0.0, cogs=10.0, fee_rate=0.15,
        flat_shipping=0.0, ad_spend=0.0, other_cost=0.0,
    ))
    assert result["revenue_amount"] == 0.0
    # Fees scale with revenue → 0 even though fee_rate is 0.15.
    assert result["marketplace_fees_amount"] == 0.0
    assert result["total_cost_amount"] == 10.0
    assert result["net_profit_amount"] == -10.0
    assert result["net_margin_percent"] is None


def test_compute_breakdown_caps_negative_inputs_at_zero():
    """A misconfigured negative `fee_rate` shouldn't produce a
    profit boost. The cap rules apply consistently to every cost
    component."""
    result = compute_breakdown(_CostInputs(
        revenue=100.0, cogs=-5.0, fee_rate=-0.5,
        flat_shipping=-2.0, ad_spend=-1.0, other_cost=-3.0,
    ))
    # All cost components clamped to 0 → total_cost is 0 → profit
    # equals revenue.
    assert result["cogs_amount"] == 0.0
    assert result["marketplace_fees_amount"] == 0.0
    assert result["shipping_cost_amount"] == 0.0
    assert result["total_cost_amount"] == 0.0
    assert result["net_profit_amount"] == 100.0
    assert result["net_margin_percent"] == 100.0


def test_compute_breakdown_handles_fee_rate_above_one():
    """Fee rate > 1.0 is operator-configurable misconfiguration —
    the engine should compute consistently (the math holds) without
    erroring. The negative profit becomes the operator's signal."""
    result = compute_breakdown(_CostInputs(
        revenue=100.0, cogs=0.0, fee_rate=1.5,
        flat_shipping=0.0, ad_spend=0.0, other_cost=0.0,
    ))
    assert result["marketplace_fees_amount"] == 150.0
    assert result["total_cost_amount"] == 150.0
    assert result["net_profit_amount"] == -50.0
    assert result["net_margin_percent"] == -50.0


# ---------------------------------------------------------------------------
# Upsert against a real DB
# ---------------------------------------------------------------------------


@pytest.fixture
def amazon_marketplace_with_fees(db: Session) -> Marketplace:
    """Amazon marketplace with a realistic 15% fee + $5 shipping."""
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


@pytest.fixture
def ml_marketplace_with_fees(db: Session) -> Marketplace:
    """ML marketplace with a realistic ~16% fee + flat shipping."""
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.16
    mp.default_shipping_cost = 10.0
    db.commit()
    db.refresh(mp)
    return mp


def _make_order_with_items(
    db: Session,
    *,
    source: OrderSource,
    total: float,
    line_items: list[tuple[str, int, float, float | None]],
    status: str = "COMPLETED",
    created_at: datetime | None = None,
) -> SalesOrder:
    """Insert a SalesOrder + SalesOrderItems. `line_items` is
    [(sku, qty, price_per_unit, cost_per_unit)]. cost_per_unit None
    means use product's cost_price as the fallback (mirrors the
    real ingestion paths' behavior)."""
    order = SalesOrder(
        status=status,
        total_price=total,
        currency="MXN",
        created_at=created_at or datetime.utcnow(),
        source=source,
        external_order_id=f"EXT-{datetime.utcnow().timestamp()}",
    )
    db.add(order)
    db.flush()

    for sku, qty, price, cost in line_items:
        product = crud_product.product.create(
            db=db,
            obj_in=ProductCreate(
                name=f"Engine {sku}", sku=sku,
                default_resale_price=price, cost_price=cost or 0.0,
            ),
        )
        db.add(SalesOrderItem(
            order_id=order.id, product_id=product.id,
            quantity=qty, price_per_unit=price, cost_per_unit=cost,
        ))
    db.commit()
    db.refresh(order)
    return order


def test_upsert_inserts_breakdown_with_marketplace_fees(
    db, amazon_marketplace_with_fees,
):
    """Happy path: an Amazon order with two line items gets a
    breakdown row keyed off the marketplace's configured fee rate +
    shipping."""
    order = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=200.0,
        line_items=[
            ("ENG-AMZN-A", 2, 50.0, 10.0),   # 2*10 = 20 cogs
            ("ENG-AMZN-B", 1, 100.0, 30.0),  # 1*30 = 30 cogs
        ],
    )

    breakdown = upsert_breakdown(db, order)
    db.commit()

    # Fees: 200 * 0.15 = 30. Shipping: 5. COGS: 50. Total: 85.
    # Profit: 200 - 85 = 115. Margin: 57.5%.
    assert breakdown.revenue_amount == 200.0
    assert breakdown.cogs_amount == 50.0
    assert breakdown.marketplace_fees_amount == 30.0
    assert breakdown.shipping_cost_amount == 5.0
    assert breakdown.total_cost_amount == 85.0
    assert breakdown.net_profit_amount == 115.0
    assert breakdown.net_margin_percent == 57.5

    # 1:1 with order; uniquely keyed.
    assert breakdown.order_id == order.id
    assert breakdown.currency == "MXN"
    # FX rate is v1-stubbed to 1.0 — every order is MXN today.
    assert breakdown.exchange_rate_to_mxn == 1.0
    assert breakdown.revenue_amount_mxn == 200.0


def test_upsert_is_idempotent_on_recompute(db, ml_marketplace_with_fees):
    """Second upsert updates the existing row in place — no duplicate
    breakdowns even when the engine re-runs the same order."""
    order = _make_order_with_items(
        db, source=OrderSource.MERCADOLIBRE, total=50.0,
        line_items=[("ENG-ML-1", 1, 50.0, 20.0)],
    )

    first = upsert_breakdown(db, order)
    db.commit()
    first_id = first.id
    first_computed_at = first.computed_at

    # Bump the marketplace fee config; re-run the engine.
    ml_marketplace_with_fees.default_fee_rate = 0.20
    db.commit()
    second = upsert_breakdown(db, order)
    db.commit()

    # Same row id (update, not insert).
    assert second.id == first_id
    # New fee rate took effect: 50 * 0.20 = 10.
    assert second.marketplace_fees_amount == 10.0
    assert second.computed_at >= first_computed_at
    # Verify the unique constraint actually held: there's exactly
    # one breakdown row for this order.
    count = (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == order.id)
        .count()
    )
    assert count == 1


def test_upsert_handles_orders_with_no_line_items(
    db, amazon_marketplace_with_fees,
):
    """A SalesOrder with no SalesOrderItems (rare but possible for
    stubs / orphaned refund rows) still gets a breakdown. COGS is 0;
    fees still scale with revenue."""
    order = SalesOrder(
        status="COMPLETED",
        total_price=100.0,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=OrderSource.AMAZON,
        external_order_id="NO-ITEMS-1",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    breakdown = upsert_breakdown(db, order)
    db.commit()
    assert breakdown.cogs_amount == 0.0
    # Fees and shipping still apply.
    assert breakdown.marketplace_fees_amount == 15.0
    assert breakdown.shipping_cost_amount == 5.0
    assert breakdown.net_profit_amount == 80.0


def test_upsert_uses_product_cost_price_when_line_item_cost_is_null(
    db, amazon_marketplace_with_fees,
):
    """The COGS fallback chain matches the existing margin report:
    `cost_per_unit` first, then `product.cost_price`. Verifies the
    legacy NULL case still produces a meaningful number."""
    order = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        # cost_per_unit=None → fallback to product.cost_price
        line_items=[("LEGACY-SKU", 1, 100.0, None)],
    )
    # Set the product's cost_price after creation.
    item = order.items[0]
    item.product.cost_price = 25.0
    db.commit()

    breakdown = upsert_breakdown(db, order)
    db.commit()
    assert breakdown.cogs_amount == 25.0


def test_upsert_safe_swallows_exceptions(db):
    """`upsert_breakdown_safe` is the ingestion-path wrapper. A
    cost-engine bug must NOT block the order from being ingested —
    the wrapper logs + returns None, the beat backfill retries on
    the next tick."""
    # Pass a stub object that crashes when accessed. The wrapper
    # should swallow it.
    class _Boom:
        @property
        def items(self):
            raise RuntimeError("simulated engine bug")
        id = 9999
        total_price = 0.0
        currency = "MXN"
        source = None

    result = upsert_breakdown_safe(db, _Boom())  # type: ignore[arg-type]
    assert result is None


def test_upsert_for_fulcrum_source_charges_no_marketplace_fees(db):
    """A FULCRUM-sourced order (storefront sale, no marketplace) has
    no fees / shipping config to read. The engine returns a
    zero-fees breakdown rather than crashing."""
    order = _make_order_with_items(
        db, source=OrderSource.FULCRUM, total=50.0,
        line_items=[("FULCRUM-1", 1, 50.0, 20.0)],
    )

    breakdown = upsert_breakdown(db, order)
    db.commit()
    assert breakdown.marketplace_fees_amount == 0.0
    assert breakdown.shipping_cost_amount == 0.0
    # COGS still applies — that's product cost, not marketplace fees.
    assert breakdown.cogs_amount == 20.0


# ---------------------------------------------------------------------------
# Bulk backfill
# ---------------------------------------------------------------------------


def test_recompute_only_missing_skips_orders_that_already_have_a_breakdown(
    db, amazon_marketplace_with_fees,
):
    """The beat-task entrypoint: `only_missing=True` skips orders
    whose breakdown is already present. This is the cheap nightly-
    backfill mode that catches anything ingested before the engine
    landed without re-writing existing rows."""
    have_breakdown = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        line_items=[("RC-EXISTING", 1, 100.0, 30.0)],
    )
    upsert_breakdown(db, have_breakdown)
    db.commit()

    no_breakdown = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=80.0,
        line_items=[("RC-MISSING", 1, 80.0, 20.0)],
    )

    summary = recompute_for_orders(db, only_missing=True)
    assert summary["breakdowns_created"] == 1
    assert summary["breakdowns_updated"] == 0
    # The pre-existing breakdown wasn't touched.
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == no_breakdown.id)
        .count() == 1
    )
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == have_breakdown.id)
        .count() == 1
    )


def test_recompute_without_only_missing_updates_all_breakdowns(
    db, amazon_marketplace_with_fees,
):
    """The default `only_missing=False` mode is for "fee rate just
    changed, recompute every breakdown". Both pre-existing and
    fresh orders get updated rows."""
    order_a = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        line_items=[("RC-ALL-A", 1, 100.0, 30.0)],
    )
    upsert_breakdown(db, order_a)
    db.commit()

    _make_order_with_items(
        db, source=OrderSource.AMAZON, total=60.0,
        line_items=[("RC-ALL-B", 1, 60.0, 15.0)],
    )

    summary = recompute_for_orders(db)
    # Order A had a breakdown already → update. Order B did not → create.
    assert summary["breakdowns_updated"] == 1
    assert summary["breakdowns_created"] == 1


def test_recompute_since_filters_to_orders_after_cutoff(
    db, amazon_marketplace_with_fees,
):
    """Operator can do `recompute_for_orders(since=last_7_days)` to
    refresh only recent orders. The `since` cursor is enforced
    against `SalesOrder.created_at`."""
    old_order = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=20.0,
        line_items=[("RC-OLD", 1, 20.0, 5.0)],
        created_at=datetime.utcnow() - timedelta(days=30),
    )
    new_order = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=50.0,
        line_items=[("RC-NEW", 1, 50.0, 10.0)],
        created_at=datetime.utcnow() - timedelta(hours=2),
    )

    cutoff = datetime.utcnow() - timedelta(days=1)
    summary = recompute_for_orders(db, since=cutoff, only_missing=True)
    assert summary["breakdowns_created"] == 1

    # Old order still has no breakdown.
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == old_order.id)
        .count() == 0
    )
    # New order does.
    assert (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == new_order.id)
        .count() == 1
    )


# ---------------------------------------------------------------------------
# Aggregate rollup
# ---------------------------------------------------------------------------


def test_aggregate_rollup_sums_columns_and_recomputes_blended_margin(
    db, amazon_marketplace_with_fees, ml_marketplace_with_fees,
):
    """The dashboard rollup uses revenue-weighted blended margin
    (not the avg of per-order margins). Mix one big high-margin
    order with a small low-margin order and verify the blended
    number reflects the dollar weighting."""
    big = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=1000.0,
        line_items=[("BIG", 1, 1000.0, 100.0)],
    )
    small = _make_order_with_items(
        db, source=OrderSource.MERCADOLIBRE, total=50.0,
        line_items=[("SMALL", 1, 50.0, 40.0)],
    )
    upsert_breakdown(db, big)
    upsert_breakdown(db, small)
    db.commit()

    rollup = aggregate_rollup(db, window_days=30)
    assert rollup["orders"] == 2
    assert rollup["revenue_amount_mxn"] == 1050.0
    # Big order: 1000 - (100 + 150 + 5) = 745 profit
    # Small order: 50 - (40 + 8 + 10) = -8 (loss)
    # Total profit: 737. Margin: 737/1050 = ~70.2%
    assert rollup["net_profit_amount"] == pytest.approx(737.0, abs=0.01)
    assert rollup["net_margin_percent"] == pytest.approx(
        (737.0 / 1050.0) * 100.0, abs=0.01,
    )


def test_aggregate_rollup_filters_by_source(
    db, amazon_marketplace_with_fees, ml_marketplace_with_fees,
):
    """`source=AMAZON` returns only the Amazon breakdown; ML is
    invisible. Lets the dashboard show per-channel rollups."""
    amzn = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        line_items=[("RP-AMZN", 1, 100.0, 20.0)],
    )
    ml = _make_order_with_items(
        db, source=OrderSource.MERCADOLIBRE, total=200.0,
        line_items=[("RP-ML", 1, 200.0, 40.0)],
    )
    upsert_breakdown(db, amzn)
    upsert_breakdown(db, ml)
    db.commit()

    amazon_rollup = aggregate_rollup(db, source=OrderSource.AMAZON)
    assert amazon_rollup["orders"] == 1
    assert amazon_rollup["revenue_amount_mxn"] == 100.0

    ml_rollup = aggregate_rollup(db, source=OrderSource.MERCADOLIBRE)
    assert ml_rollup["orders"] == 1
    assert ml_rollup["revenue_amount_mxn"] == 200.0


def test_aggregate_rollup_excludes_non_realized_statuses(
    db, amazon_marketplace_with_fees,
):
    """Cancelled/pending orders are NOT in the rollup — they bias
    the headline margin number without representing real revenue.
    The realized-status set matches the existing margin report so
    the two reports agree on what counts as a sale."""
    realized = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        line_items=[("REALIZED", 1, 100.0, 20.0)],
        status="COMPLETED",
    )
    pending = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=999.0,
        line_items=[("PENDING", 1, 999.0, 100.0)],
        status="PENDING",
    )
    upsert_breakdown(db, realized)
    upsert_breakdown(db, pending)
    db.commit()

    rollup = aggregate_rollup(db, window_days=30)
    assert rollup["orders"] == 1  # only the realized one
    assert rollup["revenue_amount_mxn"] == 100.0


def test_aggregate_rollup_excludes_orders_outside_window(
    db, amazon_marketplace_with_fees,
):
    """`window_days` is enforced against `SalesOrder.created_at`."""
    recent = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=100.0,
        line_items=[("WIN-RECENT", 1, 100.0, 20.0)],
        created_at=datetime.utcnow() - timedelta(hours=2),
    )
    old = _make_order_with_items(
        db, source=OrderSource.AMAZON, total=999.0,
        line_items=[("WIN-OLD", 1, 999.0, 50.0)],
        created_at=datetime.utcnow() - timedelta(days=60),
    )
    upsert_breakdown(db, recent)
    upsert_breakdown(db, old)
    db.commit()

    rollup = aggregate_rollup(db, window_days=30)
    assert rollup["orders"] == 1
    assert rollup["revenue_amount_mxn"] == 100.0


def test_aggregate_rollup_handles_empty_window(db):
    """A window with no orders returns zeros + None margin. Avoids
    the dashboard rendering a NaN/Infinity number when the seller
    has no recent sales."""
    rollup = aggregate_rollup(db, window_days=30)
    assert rollup["orders"] == 0
    assert rollup["revenue_amount_mxn"] == 0.0
    assert rollup["net_margin_percent"] is None


# ---------------------------------------------------------------------------
# Ingestion-path hooks (regression guard for the inline upsert calls)
# ---------------------------------------------------------------------------


def test_ingestion_paths_import_the_cost_engine_helper():
    """Sanity check that the post-ingest hooks are wired. Failing
    here means someone deleted the inline upsert call without
    realising it disables the inline analytics for new orders.
    """
    from src.services import amazon_order_ingestion
    from src.services import mercadolibre_order_ingestion

    src_amzn = open(amazon_order_ingestion.__file__).read()
    src_ml = open(mercadolibre_order_ingestion.__file__).read()
    assert "upsert_breakdown_safe" in src_amzn
    assert "upsert_breakdown_safe" in src_ml


# ---------------------------------------------------------------------------
# Celery task wiring
# ---------------------------------------------------------------------------


def test_cost_engine_celery_task_is_registered_and_scheduled():
    """The beat schedule entry must point at the registered task
    name. A typo would mean the backfill silently doesn't fire."""
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401 — register task

    assert "src.tasks.backfill_order_cost_breakdowns" in celery_app.tasks
    schedule = celery_app.conf.beat_schedule
    assert "cost-engine-backfill" in schedule
    assert (
        schedule["cost-engine-backfill"]["task"]
        == "src.tasks.backfill_order_cost_breakdowns"
    )


def test_cost_engine_celery_task_delegates_to_recompute():
    from unittest.mock import MagicMock, patch
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)
    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.order_cost_engine.recompute_for_orders",
            return_value={"breakdowns_created": 2, "breakdowns_updated": 0, "errors": 0},
        ) as mock_recompute,
    ):
        result = task_module.backfill_order_cost_breakdowns()
    assert result["breakdowns_created"] == 2
    mock_recompute.assert_called_once()
    fake_session.close.assert_called_once()
