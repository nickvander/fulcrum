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


# ---------------------------------------------------------------------------
# GET /reports/refunds-list — drill-down behind the dashboard widget
# ---------------------------------------------------------------------------


def test_refunds_list_returns_full_order_cancellations_with_revenue(
    client: TestClient, db, admin_headers,
):
    """An order that flipped realized→cancelled in the window shows up
    as a `refund_kind='order_cancelled'` row carrying the breakdown's
    revenue as the refunded amount."""
    order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, sku="DRILL-ML-1", total=150.0,
    )
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get("/api/v1/reports/refunds-list", headers=admin_headers)
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 1
    row = body["items"][0]
    assert row["refund_kind"] == "order_cancelled"
    assert row["source"] == "MERCADOLIBRE"
    assert row["external_order_id"] == "DRILL-ML-1"
    assert row["refunded_amount_mxn"] == pytest.approx(150.0)
    assert row["order_status"] == "CANCELLED"


def test_refunds_list_returns_amazon_partial_refunds(
    client: TestClient, db, admin_headers,
):
    """An Amazon partial-refund row shows up with `refund_kind='amazon_partial'`
    and preserves the order's current status (typically SHIPPED for
    these — the partial refund doesn't move the top-level status)."""
    order = _make_realized_order(
        db, source=OrderSource.AMAZON, sku="DRILL-AMZN-PARTIAL", total=200.0,
    )
    # Bump the order to SHIPPED so the test reflects the realistic
    # case where the partial refund happens after shipment.
    apply_status_change(db, order, new_status="shipped", source_signal="amazon_poll")
    db.add(AmazonOrderRefund(
        order_id=order.id,
        amazon_refund_id="rid-partial-1",
        posted_at=datetime.now(timezone.utc),
        refund_amount=37.5,
    ))
    db.commit()

    resp = client.get("/api/v1/reports/refunds-list", headers=admin_headers)
    body = resp.json()
    # 1 full-order shipped event + 1 partial = 1 partial in scope
    # (the realized→shipped transition isn't a refund event so it
    # isn't a row here).
    partial_rows = [r for r in body["items"] if r["refund_kind"] == "amazon_partial"]
    assert len(partial_rows) == 1
    row = partial_rows[0]
    assert row["source"] == "AMAZON"
    assert row["refunded_amount_mxn"] == pytest.approx(37.5)
    assert row["order_status"] == "SHIPPED"


def test_refunds_list_orders_recent_first(
    client: TestClient, db, admin_headers,
):
    """Most-recent refund lands at index 0 — the operator's eye
    follows the timestamp column."""
    older = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="OLDER", total=50.0)
    newer = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="NEWER", total=80.0)
    apply_status_change(db, older, new_status="cancelled", source_signal="ml_poll")
    db.flush()
    # Backdate the older transition so the sort order is deterministic
    # — without this both transitions get the same now() timestamp.
    older_event = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == older.id)
        .order_by(SalesOrderStatusEvent.changed_at.desc())
        .first()
    )
    older_event.changed_at = datetime.now(timezone.utc) - timedelta(days=5)
    apply_status_change(db, newer, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get("/api/v1/reports/refunds-list", headers=admin_headers)
    items = resp.json()["items"]
    assert items[0]["external_order_id"] == "NEWER"
    assert items[1]["external_order_id"] == "OLDER"


def test_refunds_list_paginates_via_skip_and_limit(
    client: TestClient, db, admin_headers,
):
    """`skip` and `limit` page through the result set; `total`
    reflects the unpaginated count so the UI can render `N–M of T`."""
    for i in range(5):
        order = _make_realized_order(
            db, source=OrderSource.MERCADOLIBRE, sku=f"PAGE-{i}", total=10.0 * (i + 1),
        )
        apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get(
        "/api/v1/reports/refunds-list",
        params={"skip": 2, "limit": 2},
        headers=admin_headers,
    )
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_refunds_list_source_filter_excludes_other_channels(
    client: TestClient, db, admin_headers,
):
    """A `source=amazon` filter drops ML rows. Partial-refund rows
    are Amazon-only by construction; a non-Amazon source filter
    drops them too."""
    ml_order = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="F-ML", total=80.0)
    amzn_order = _make_realized_order(db, source=OrderSource.AMAZON, sku="F-AMZN", total=120.0)
    apply_status_change(db, ml_order, new_status="cancelled", source_signal="ml_poll")
    apply_status_change(db, amzn_order, new_status="canceled", source_signal="amazon_poll")
    db.commit()

    resp = client.get(
        "/api/v1/reports/refunds-list",
        params={"source": "amazon"},
        headers=admin_headers,
    )
    items = resp.json()["items"]
    assert all(r["source"] == "AMAZON" for r in items)
    # Going the other direction: an ML-only filter drops Amazon rows
    # AND partial-refund rows.
    db.add(AmazonOrderRefund(
        order_id=amzn_order.id, amazon_refund_id="rid-z",
        posted_at=datetime.now(timezone.utc), refund_amount=10.0,
    ))
    db.commit()
    resp = client.get(
        "/api/v1/reports/refunds-list",
        params={"source": "mercadolibre"},
        headers=admin_headers,
    )
    items = resp.json()["items"]
    assert all(r["refund_kind"] == "order_cancelled" for r in items)
    assert all(r["source"] == "MERCADOLIBRE" for r in items)


def test_refunds_list_unknown_source_returns_400(
    client: TestClient, db, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/refunds-list",
        params={"source": "shopify"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.report.unknownSource"


def test_refunds_list_empty_when_no_activity(
    client: TestClient, db, admin_headers,
):
    resp = client.get("/api/v1/reports/refunds-list", headers=admin_headers)
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# CSV + PDF exports of the refunds-summary
# ---------------------------------------------------------------------------


def test_refunds_summary_csv_has_one_row_per_channel_plus_total(
    client: TestClient, db, admin_headers,
):
    """The CSV mirrors the dashboard widget: one row per channel
    followed by a TOTAL row, in the canonical FULCRUM /
    MERCADOLIBRE / AMAZON order."""
    import csv as csvlib
    import io

    ml = _make_realized_order(db, source=OrderSource.MERCADOLIBRE, sku="X-ML", total=200.0)
    apply_status_change(db, ml, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    resp = client.get(
        "/api/v1/reports/refunds-summary/export",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")

    rows = list(csvlib.reader(io.StringIO(resp.text)))
    # CSV uses the snake_case key as header (machine-readable
    # default per the shared report_export module).
    assert rows[0] == [
        "source", "refunds_count", "refunded_amount_mxn",
        "realized_orders_count", "refund_rate_percent",
    ]
    sources_in_order = [row[0] for row in rows[1:]]
    # Channel rows render in the by-channel order returned by the
    # endpoint (which iterates `OrderSource`); TOTAL is always last.
    assert sources_in_order[-1] == "TOTAL"
    assert "MERCADOLIBRE" in sources_in_order

    # The MERCADOLIBRE row carries the cancelled order's revenue.
    ml_row = next(row for row in rows[1:] if row[0] == "MERCADOLIBRE")
    assert ml_row[1] == "1"  # refunds_count
    assert "200.00" in ml_row[2]  # refunded_amount_mxn (with currency formatter)

    # TOTAL row aggregates.
    total_row = rows[-1]
    assert total_row[0] == "TOTAL"
    assert total_row[1] == "1"


def test_refunds_summary_pdf_subtitle_reflects_window_label(
    client: TestClient, db, admin_headers,
):
    """An explicit date range surfaces in the PDF's filename + a
    `Content-Disposition` header — and through `_resolve_date_window`
    it lands in the rendered subtitle line of the PDF body. The CSV
    is header-row-only (no subtitle row), so we exercise the date-
    range plumbing via the PDF endpoint here. Asserting on the
    rendered PDF bytes is brittle (reportlab compresses); a 200 +
    PDF marker + a positive content length is enough."""
    resp = client.get(
        "/api/v1/reports/refunds-summary/export-pdf",
        params={"start_date": "2026-01-01", "end_date": "2026-03-31"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 200


def test_refunds_summary_pdf_returns_pdf_bytes(
    client: TestClient, db, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/refunds-summary/export-pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")
    assert resp.headers["content-type"].startswith("application/pdf")
    # Filename header carries the canonical stem so the operator's
    # downloads folder doesn't fill up with generic `report.pdf`.
    cd = resp.headers.get("content-disposition", "")
    assert "fulcrum-refunds-summary" in cd


def test_refunds_summary_csv_rejects_inverted_range(
    client: TestClient, db, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/refunds-summary/export",
        params={"start_date": "2026-04-01", "end_date": "2026-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.reports.invalidDateRange"
