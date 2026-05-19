"""
Track 2 dashboard-widget endpoints:

  - GET /api/v1/reports/cost-rollup/by-channel
  - GET /api/v1/reports/cost-rollup/daily
  - GET /api/v1/reports/top-movers

Each is a thin wrapper over a helper in `order_cost_engine.py`. The
math is covered at the service-helper level too — this file focuses
on the HTTP contract (auth, query params, response shape) + the
helpers' behavior at the boundaries (empty windows, zero-revenue
products, the daily series's gap-filling).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.marketplace import Marketplace
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate
from src.services.order_cost_engine import (
    aggregate_daily_series,
    aggregate_rollup_by_channel,
    top_movers,
    upsert_breakdown,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _ensure_amazon(db: Session) -> Marketplace:
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


def _ensure_ml(db: Session) -> Marketplace:
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


def _seed_order(
    db: Session,
    *,
    source: OrderSource,
    total: float,
    lines: list[tuple[str, int, float, float | None]],
    status: str = "COMPLETED",
    created_at: datetime | None = None,
) -> SalesOrder:
    """Insert SalesOrder + items + breakdown. Reuses crud_product so
    products created across tests have unique SKUs."""
    order = SalesOrder(
        status=status,
        total_price=total,
        currency="MXN",
        created_at=created_at or datetime.utcnow(),
        source=source,
        external_order_id=f"T2-{datetime.utcnow().timestamp()}-{lines[0][0]}",
    )
    db.add(order)
    db.flush()
    for sku, qty, price, cost in lines:
        product = crud_product.product.create(
            db=db,
            obj_in=ProductCreate(
                name=f"T2 {sku}", sku=sku,
                default_resale_price=price, cost_price=cost or 0.0,
            ),
        )
        db.add(SalesOrderItem(
            order_id=order.id, product_id=product.id,
            quantity=qty, price_per_unit=price, cost_per_unit=cost,
        ))
    db.commit()
    upsert_breakdown(db, order)
    db.commit()
    return order


# ---------------------------------------------------------------------------
# aggregate_rollup_by_channel — service helper
# ---------------------------------------------------------------------------


def test_by_channel_returns_one_row_per_source_with_orders(db):
    """Three channels, two with sales, one without → two rows in
    descending revenue order. The empty channel is omitted (don't
    waste a stacked-bar slot on it)."""
    _ensure_amazon(db)
    _ensure_ml(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=500.0, lines=[("BC-AMZN", 1, 500.0, 100.0)],
    )
    _seed_order(
        db, source=OrderSource.MERCADOLIBRE,
        total=200.0, lines=[("BC-ML", 1, 200.0, 50.0)],
    )

    rows = aggregate_rollup_by_channel(db, window_days=30)
    assert len(rows) == 2
    # Highest-revenue channel first.
    assert rows[0]["source"] == OrderSource.AMAZON.value
    assert rows[1]["source"] == OrderSource.MERCADOLIBRE.value
    assert rows[0]["revenue_amount_mxn"] == 500.0
    assert rows[1]["revenue_amount_mxn"] == 200.0
    assert rows[0]["orders"] == 1
    # Fees + shipping populated from each marketplace's config.
    assert rows[0]["marketplace_fees_amount"] == 75.0
    assert rows[1]["marketplace_fees_amount"] == 32.0


def test_by_channel_excludes_channels_with_zero_orders(db):
    """A marketplace exists but has no realized orders → its row
    must NOT appear in the channel list."""
    _ensure_amazon(db)
    _ensure_ml(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("BC-ONLY-AMZN", 1, 100.0, 25.0)],
    )

    rows = aggregate_rollup_by_channel(db, window_days=30)
    assert len(rows) == 1
    assert rows[0]["source"] == OrderSource.AMAZON.value


def test_by_channel_endpoint_round_trips(client: TestClient, db, admin_headers):
    _ensure_amazon(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("BC-API-1", 1, 100.0, 20.0)],
    )

    response = client.get(
        "/api/v1/reports/cost-rollup/by-channel?window_days=30",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["window_days"] == 30
    assert len(body["channels"]) == 1
    assert body["channels"][0]["source"] == "AMAZON"


def test_by_channel_endpoint_requires_auth(client: TestClient):
    response = client.get("/api/v1/reports/cost-rollup/by-channel")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# aggregate_daily_series — service helper
# ---------------------------------------------------------------------------


def test_daily_series_emits_one_row_per_day_in_window(db):
    """A 7-day window emits 8 days (cutoff is INCLUSIVE of both
    endpoints — the cutoff_date itself + today's date). The chart
    needs continuous days so the x-axis doesn't skip."""
    _ensure_amazon(db)
    series = aggregate_daily_series(db, window_days=7)
    assert len(series) == 8  # cutoff date + 6 days + today


def test_daily_series_buckets_orders_by_calendar_day(db):
    """Two orders on the same day are summed into one row; an
    order on a different day lands in its own row."""
    _ensure_amazon(db)
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)

    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("DS-TODAY-A", 1, 100.0, 20.0)],
        created_at=today,
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=50.0, lines=[("DS-TODAY-B", 1, 50.0, 10.0)],
        created_at=today,
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=30.0, lines=[("DS-YDAY", 1, 30.0, 5.0)],
        created_at=yesterday,
    )

    series = aggregate_daily_series(db, window_days=7)
    by_day = {row["date"]: row for row in series}

    assert by_day[today.date().isoformat()]["orders"] == 2
    assert by_day[today.date().isoformat()]["revenue_amount_mxn"] == 150.0
    assert by_day[yesterday.date().isoformat()]["orders"] == 1
    assert by_day[yesterday.date().isoformat()]["revenue_amount_mxn"] == 30.0


def test_daily_series_fills_quiet_days_with_zeros(db):
    """Days with no orders appear with `orders=0` and zero values —
    the chart needs a continuous line. Otherwise quiet days would
    look like data dropout."""
    _ensure_amazon(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("DS-FILL", 1, 100.0, 20.0)],
        created_at=datetime.utcnow() - timedelta(days=3),
    )

    series = aggregate_daily_series(db, window_days=7)
    zero_days = [row for row in series if row["orders"] == 0]
    # 7-day window emits 8 rows; only 1 has an order → 7 are zeros.
    assert len(zero_days) == 7
    for row in zero_days:
        assert row["revenue_amount_mxn"] == 0.0
        assert row["net_profit_amount"] == 0.0


def test_daily_series_excludes_non_realized_status(db):
    """Pending / cancelled orders don't bias the line — only realized
    statuses contribute. Same rule the headline rollup applies."""
    _ensure_amazon(db)
    today = datetime.utcnow()
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("DS-REAL", 1, 100.0, 20.0)],
        status="COMPLETED",
        created_at=today,
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=9999.0, lines=[("DS-PEND", 1, 9999.0, 100.0)],
        status="PENDING",
        created_at=today,
    )

    series = aggregate_daily_series(db, window_days=7)
    today_row = next(r for r in series if r["date"] == today.date().isoformat())
    # Only the COMPLETED order counted.
    assert today_row["orders"] == 1
    assert today_row["revenue_amount_mxn"] == 100.0


def test_daily_endpoint_round_trips(client: TestClient, db, admin_headers):
    _ensure_amazon(db)
    response = client.get(
        "/api/v1/reports/cost-rollup/daily?window_days=14",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 14
    assert len(body["series"]) == 15  # 14 + today


def test_daily_endpoint_requires_auth(client: TestClient):
    assert client.get("/api/v1/reports/cost-rollup/daily").status_code == 401


# ---------------------------------------------------------------------------
# top_movers — service helper
# ---------------------------------------------------------------------------


def test_top_movers_orders_by_revenue_and_respects_limit(db):
    """Three products with varying revenue. limit=2 returns the two
    biggest in revenue-desc order."""
    _ensure_amazon(db)
    # Each separate order so the breakdown is straightforward.
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=300.0, lines=[("TM-BIG", 3, 100.0, 20.0)],
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=200.0, lines=[("TM-MED", 1, 200.0, 50.0)],
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=50.0, lines=[("TM-SMALL", 1, 50.0, 10.0)],
    )

    rows = top_movers(db, window_days=30, limit=2)
    assert len(rows) == 2
    assert rows[0]["sku"] == "TM-BIG"
    assert rows[1]["sku"] == "TM-MED"
    assert rows[0]["units"] == 3
    assert rows[0]["revenue_amount"] == 300.0


def test_top_movers_includes_net_margin_with_pro_rated_overhead(db):
    """Each product gets a pro-rated share of its order's fees +
    shipping (overhead). A single-line order should attribute the
    full overhead to that line."""
    _ensure_amazon(db)
    # Amazon: 15% fee + $5 shipping on a $100 order = $20 overhead.
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("TM-OV", 1, 100.0, 30.0)],
    )

    rows = top_movers(db, window_days=30, limit=1)
    assert len(rows) == 1
    row = rows[0]
    assert row["cogs_amount"] == 30.0
    assert row["overhead_amount"] == 20.0   # 15 fees + 5 shipping
    assert row["total_cost_amount"] == 50.0
    assert row["net_profit_amount"] == 50.0
    assert row["net_margin_percent"] == 50.0


def test_top_movers_pro_rates_overhead_across_a_multi_line_order(db):
    """A two-line order with $30 overhead: line A is 70% of revenue
    → gets $21; line B is 30% → gets $9. Test the share math."""
    _ensure_amazon(db)
    # 70 + 30 = 100 revenue. Amazon fees 15 + shipping 5 = $20 overhead.
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0,
        lines=[
            ("TM-PRO-A", 1, 70.0, 10.0),  # 70% share
            ("TM-PRO-B", 1, 30.0, 5.0),   # 30% share
        ],
    )

    rows = top_movers(db, window_days=30, limit=10)
    by_sku = {r["sku"]: r for r in rows}
    # 70% of $20 = $14, 30% of $20 = $6.
    assert by_sku["TM-PRO-A"]["overhead_amount"] == 14.0
    assert by_sku["TM-PRO-B"]["overhead_amount"] == 6.0


def test_top_movers_excludes_non_realized_statuses(db):
    """A PENDING order's lines don't count, even if revenue is huge.
    Same realized-status rule as the headline rollup."""
    _ensure_amazon(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=100.0, lines=[("TM-REAL", 1, 100.0, 20.0)],
        status="COMPLETED",
    )
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=9999.0, lines=[("TM-FAKE", 1, 9999.0, 0.0)],
        status="PENDING",
    )

    rows = top_movers(db, window_days=30, limit=10)
    skus = [r["sku"] for r in rows]
    assert "TM-REAL" in skus
    assert "TM-FAKE" not in skus


def test_top_movers_empty_when_no_orders(db):
    """Empty window → empty list, not an exception. Dashboard
    renders an empty-state."""
    rows = top_movers(db, window_days=30, limit=10)
    assert rows == []


def test_top_movers_endpoint_round_trips(client: TestClient, db, admin_headers):
    _ensure_amazon(db)
    _seed_order(
        db, source=OrderSource.AMAZON,
        total=200.0, lines=[("TM-API", 2, 100.0, 30.0)],
    )

    response = client.get(
        "/api/v1/reports/top-movers?window_days=30&limit=5",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 30
    assert body["limit"] == 5
    assert len(body["rows"]) == 1
    assert body["rows"][0]["sku"] == "TM-API"


def test_top_movers_endpoint_requires_auth(client: TestClient):
    assert client.get("/api/v1/reports/top-movers").status_code == 401
