"""End-to-end coverage for `GET /api/v1/reports/refunds-summary`.

Two sources contribute to the rollup: status transitions out of
the realized set (full-order refunds/cancellations) and the
`amazon_order_refunds` table (Amazon partial refunds). The tests
cover both, plus window filtering and rate math.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import (
    AmazonOrderRefund,
    OrderSource,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatusEvent,
)
from src.schemas.product import ProductCreate
from src.services import order_cost_engine
from src.services.order_lifecycle import (
    apply_status_change,
    record_initial_status,
)


pytestmark = pytest.mark.db


def _make_realized_order(
    db: Session,
    *,
    source: OrderSource,
    sku: str,
    total: float = 100.0,
    created_at: datetime | None = None,
) -> SalesOrder:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"R-{sku}", sku=sku,
            default_resale_price=total, cost_price=total * 0.4,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=100, location="default"))
    order = SalesOrder(
        status="PAID",
        total_price=total,
        currency="MXN",
        created_at=created_at or datetime.utcnow(),
        source=source,
        external_order_id=sku,
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=1, price_per_unit=total, cost_per_unit=total * 0.4,
    ))
    db.commit()
    db.refresh(order)
    order_cost_engine.upsert_breakdown(db, order)
    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()
    return order


def test_refunds_summary_counts_full_order_cancellations(
    client: TestClient, db, admin_headers,
):
    """A PAID → CANCELLED transition shows up in the source's
    refunds_count + refunded_amount_mxn (sum of breakdown revenue)."""
    order = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="REF-ML-1", total=150.0)
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    by_channel = {row["source"]: row for row in body["by_channel"]}
    assert by_channel["MERCADOLIBRE"]["refunds_count"] == 1
    assert by_channel["MERCADOLIBRE"]["refunded_amount_mxn"] == pytest.approx(150.0)


def test_refunds_summary_includes_amazon_partial_refunds(
    client: TestClient, db, admin_headers,
):
    """Amazon partial refunds attribute to AMAZON via the
    `amazon_order_refunds` table — they don't require a status
    transition."""
    order = _make_realized_order(db, source=OrderSource.AMAZON, sku="REF-AMZN-1", total=200.0)
    db.add(AmazonOrderRefund(
        order_id=order.id,
        amazon_refund_id="rid-1",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        refund_amount=25.0,
        currency="MXN",
    ))
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    body = resp.json()
    amzn = next(r for r in body["by_channel"] if r["source"] == "AMAZON")
    assert amzn["refunds_count"] == 1
    assert amzn["refunded_amount_mxn"] == pytest.approx(25.0)


def test_refunds_summary_full_plus_partial_amazon(
    client: TestClient, db, admin_headers,
):
    """When the same Amazon credential has BOTH a full cancellation
    and a partial refund, both contribute to the rollup."""
    full = _make_realized_order(db, source=OrderSource.AMAZON, sku="REF-AMZN-FULL", total=300.0)
    partial = _make_realized_order(db, source=OrderSource.AMAZON, sku="REF-AMZN-PARTIAL", total=200.0)
    apply_status_change(db, full, new_status="canceled", source_signal="amazon_poll")
    db.add(AmazonOrderRefund(
        order_id=partial.id,
        amazon_refund_id="rid-x",
        posted_at=datetime.now(timezone.utc),
        refund_amount=40.0,
    ))
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    body = resp.json()
    amzn = next(r for r in body["by_channel"] if r["source"] == "AMAZON")
    assert amzn["refunds_count"] == 2
    # 300 (full) + 40 (partial) = 340
    assert amzn["refunded_amount_mxn"] == pytest.approx(340.0)


def test_refunds_summary_rate_computed_against_realized_orders(
    client: TestClient, db, admin_headers,
):
    """refund_rate_percent = refunds / realized-orders × 100."""
    # 4 realized ML orders, 1 of them cancelled → 25% rate.
    cancelled = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="RATE-1", total=100.0)
    for sku in ("RATE-2", "RATE-3", "RATE-4"):
        _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku=sku, total=100.0)
    apply_status_change(db, cancelled, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    body = resp.json()
    ml = next(r for r in body["by_channel"] if r["source"] == "MERCADOLIBRE")
    assert ml["realized_orders_count"] == 3  # cancelled order isn't realized any more
    assert ml["refunds_count"] == 1
    # 1 refund / 3 realized = ~33.33%
    assert ml["refund_rate_percent"] == pytest.approx(33.33)


def test_refunds_summary_rate_is_null_when_no_orders(
    client: TestClient, db, admin_headers,
):
    """Empty window → rate is None, not 0%, so the operator doesn't
    misread an empty channel as a perfect channel."""
    resp = client.get(
        "/api/v1/reports/refunds-summary",
        params={"window_days": 1},
        headers=admin_headers,
    )
    body = resp.json()
    for row in body["by_channel"]:
        assert row["refund_rate_percent"] is None


def test_refunds_summary_dedups_repeated_cancellation_transitions(
    client: TestClient, db, admin_headers,
):
    """An order that bounces realized→cancelled→realized→cancelled in
    the window counts ONCE — the operator cares about distinct
    refunded orders, not transition events."""
    order = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="BOUNCE-1", total=80.0)
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    apply_status_change(db, order, new_status="paid", source_signal="manual")
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    body = resp.json()
    ml = next(r for r in body["by_channel"] if r["source"] == "MERCADOLIBRE")
    assert ml["refunds_count"] == 1


def test_refunds_summary_honors_explicit_date_range(
    client: TestClient, db, admin_headers,
):
    """A transition outside the window is excluded; reuse the shared
    `_resolve_date_window` semantics."""
    old_order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, sku="OLD-1",
        total=99.0, created_at=datetime.utcnow() - timedelta(days=120),
    )
    # Force the transition timestamp to also be 120 days ago.
    apply_status_change(db, old_order, new_status="cancelled", source_signal="ml_poll")
    db.flush()
    old_event = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == old_order.id)
        .order_by(SalesOrderStatusEvent.changed_at.desc())
        .first()
    )
    old_event.changed_at = datetime.now(timezone.utc) - timedelta(days=120)
    db.commit()

    resp = client.get(
        "/api/v1/reports/refunds-summary",
        params={"window_days": 30},
        headers=admin_headers,
    )
    body = resp.json()
    ml = next(r for r in body["by_channel"] if r["source"] == "MERCADOLIBRE")
    assert ml["refunds_count"] == 0


def test_refunds_summary_totals_aggregate_across_channels(
    client: TestClient, db, admin_headers,
):
    """`totals` row sums across every channel; rate uses the same
    cross-channel denominator."""
    ml_cancel = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="T-ML", total=100.0)
    amzn_partial_order = _make_realized_order(db, source=OrderSource.AMAZON, sku="T-AMZN", total=200.0)
    apply_status_change(db, ml_cancel, new_status="cancelled", source_signal="ml_poll")
    db.add(AmazonOrderRefund(
        order_id=amzn_partial_order.id,
        amazon_refund_id="rid-t",
        posted_at=datetime.now(timezone.utc),
        refund_amount=50.0,
    ))
    db.commit()

    resp = client.get("/api/v1/reports/refunds-summary", headers=admin_headers)
    body = resp.json()
    totals = body["totals"]
    # 1 ML full + 1 Amazon partial = 2 refunds
    assert totals["refunds_count"] == 2
    # 100 (ML) + 50 (Amazon partial) = 150
    assert totals["refunded_amount_mxn"] == pytest.approx(150.0)
    assert totals["source"] == "ALL"


def test_refunds_summary_rejects_inverted_range(
    client: TestClient, db, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/refunds-summary",
        params={"start_date": "2026-04-01", "end_date": "2026-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.reports.invalidDateRange"
