"""Coverage for the reason-code summary report.

  - GET /reports/reason-code-summary (JSON rollup)
  - GET /reports/reason-code-summary/export (CSV)
  - GET /reports/reason-code-summary/export-pdf (PDF)

The endpoint aggregates inventory_adjustments rows by reason_code
over the window. Each row reports adjustments_count + signed
total_units_delta + total_capital_at_cost (= sum of |adjustment|
× current cost_price). Legacy NULL rows roll up under the literal
`"none"` source so they're visible without a special query.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryAdjustment
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


def _seed_adj(
    db: Session, *, sku: str, adjustment: int, cost_price: float,
    reason_code: str | None, when: datetime | None = None,
) -> int:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"RC {sku}", sku=sku,
            default_resale_price=cost_price * 2, cost_price=cost_price,
        ),
    )
    db.add(InventoryAdjustment(
        product_id=product.id,
        adjustment=adjustment,
        reason="seed",
        reason_code=reason_code,
        timestamp=when or datetime.utcnow(),
        created_by="test",
    ))
    db.commit()
    return product.id


# ---------------------------------------------------------------------------
# JSON endpoint
# ---------------------------------------------------------------------------


def test_summary_rolls_up_by_reason_code(client: TestClient, db, admin_headers):
    """5 shrinkage rows at $10 cost = $50 capital + 5 adjustments, all
    negative. Damage row at $20 cost = $20 capital, 1 adjustment."""
    for i in range(5):
        _seed_adj(db, sku=f"SHR-{i}", adjustment=-1, cost_price=10.0, reason_code="shrinkage")
    _seed_adj(db, sku="DMG-1", adjustment=-1, cost_price=20.0, reason_code="damage")

    resp = client.get("/api/v1/reports/reason-code-summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    by_code = {r["reason_code"]: r for r in body["rows"]}

    assert by_code["shrinkage"]["adjustments_count"] == 5
    assert by_code["shrinkage"]["total_units_delta"] == -5
    assert by_code["shrinkage"]["total_capital_at_cost"] == pytest.approx(50.0)

    assert by_code["damage"]["adjustments_count"] == 1
    assert by_code["damage"]["total_units_delta"] == -1
    assert by_code["damage"]["total_capital_at_cost"] == pytest.approx(20.0)


def test_summary_capital_uses_absolute_value(client: TestClient, db, admin_headers):
    """A return (positive adjustment) and a sale (negative) of the
    same SKU both contribute their |adjustment| × cost_price to the
    capital metric — we're measuring how much value MOVED, not net
    direction. `total_units_delta` carries the sign separately for
    operators that want it."""
    pid = _seed_adj(db, sku="MIX-1", adjustment=+3, cost_price=10.0, reason_code="return")
    db.add(InventoryAdjustment(
        product_id=pid, adjustment=-2, reason="sale", reason_code="sale",
        timestamp=datetime.utcnow(), created_by="test",
    ))
    db.commit()

    resp = client.get("/api/v1/reports/reason-code-summary", headers=admin_headers)
    by_code = {r["reason_code"]: r for r in resp.json()["rows"]}
    assert by_code["return"]["total_capital_at_cost"] == pytest.approx(30.0)  # |+3| × 10
    assert by_code["sale"]["total_capital_at_cost"] == pytest.approx(20.0)    # |-2| × 10
    assert by_code["return"]["total_units_delta"] == 3
    assert by_code["sale"]["total_units_delta"] == -2


def test_summary_surfaces_legacy_null_rows_under_none(
    client: TestClient, db, admin_headers,
):
    """Legacy uncategorized rows (reason_code IS NULL) roll up under
    the literal `'none'` source so the operator sees them in the
    rollup without writing a custom NULL query."""
    _seed_adj(db, sku="LEG-1", adjustment=-1, cost_price=5.0, reason_code=None)
    _seed_adj(db, sku="LEG-2", adjustment=-2, cost_price=5.0, reason_code=None)

    resp = client.get("/api/v1/reports/reason-code-summary", headers=admin_headers)
    by_code = {r["reason_code"]: r for r in resp.json()["rows"]}
    assert "none" in by_code
    assert by_code["none"]["adjustments_count"] == 2
    assert by_code["none"]["total_units_delta"] == -3
    assert by_code["none"]["total_capital_at_cost"] == pytest.approx(15.0)


def test_summary_orders_by_capital_at_risk_desc(
    client: TestClient, db, admin_headers,
):
    """Capital-at-risk desc lets the operator's eye land on the
    biggest dollar impact first regardless of category."""
    _seed_adj(db, sku="SMALL-1", adjustment=-1, cost_price=5.0, reason_code="shrinkage")
    _seed_adj(db, sku="BIG-1", adjustment=-10, cost_price=50.0, reason_code="damage")

    resp = client.get("/api/v1/reports/reason-code-summary", headers=admin_headers)
    rows = resp.json()["rows"]
    # damage has $500 capital, shrinkage has $5 — damage lands first.
    assert rows[0]["reason_code"] == "damage"
    assert rows[1]["reason_code"] == "shrinkage"


def test_summary_excludes_rows_outside_the_window(
    client: TestClient, db, admin_headers,
):
    """A row 90 days old isn't in the default 30d window."""
    long_ago = datetime.utcnow() - timedelta(days=90)
    _seed_adj(db, sku="OLD-1", adjustment=-1, cost_price=10.0, reason_code="shrinkage", when=long_ago)
    _seed_adj(db, sku="NEW-1", adjustment=-1, cost_price=10.0, reason_code="shrinkage")

    resp = client.get(
        "/api/v1/reports/reason-code-summary",
        params={"window_days": 30},
        headers=admin_headers,
    )
    by_code = {r["reason_code"]: r for r in resp.json()["rows"]}
    # Only the recent row contributes.
    assert by_code["shrinkage"]["adjustments_count"] == 1


def test_summary_explicit_date_range_overrides_window_days(
    client: TestClient, db, admin_headers,
):
    """`start_date`/`end_date` pin the window irrespective of
    `window_days`, matching the velocity/margin/stockout semantics."""
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    _seed_adj(
        db, sku="ANCIENT", adjustment=-3, cost_price=5.0,
        reason_code="shrinkage", when=one_year_ago,
    )

    # 30-day window misses it.
    short_resp = client.get(
        "/api/v1/reports/reason-code-summary",
        headers=admin_headers,
    )
    assert short_resp.json()["rows"] == []

    # Explicit range covers a year — finds it.
    long_resp = client.get(
        "/api/v1/reports/reason-code-summary",
        params={
            "start_date": (datetime.utcnow() - timedelta(days=400)).date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat(),
        },
        headers=admin_headers,
    )
    rows = long_resp.json()["rows"]
    by_code = {r["reason_code"]: r for r in rows}
    assert by_code["shrinkage"]["adjustments_count"] == 1


def test_summary_empty_when_no_adjustments(
    client: TestClient, db, admin_headers,
):
    resp = client.get("/api/v1/reports/reason-code-summary", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["rows"] == []


def test_summary_rejects_inverted_range(client: TestClient, admin_headers):
    resp = client.get(
        "/api/v1/reports/reason-code-summary",
        params={"start_date": "2026-04-01", "end_date": "2026-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.reports.invalidDateRange"


# ---------------------------------------------------------------------------
# CSV + PDF exports
# ---------------------------------------------------------------------------


def test_csv_export_columns_and_one_row_per_code(
    client: TestClient, db, admin_headers,
):
    """The export emits one row per reason_code with the canonical
    snake_case headers (machine-readable per the shared
    report_export module)."""
    _seed_adj(db, sku="CSV-S", adjustment=-2, cost_price=10.0, reason_code="shrinkage")
    _seed_adj(db, sku="CSV-D", adjustment=-1, cost_price=5.0, reason_code="damage")

    resp = client.get(
        "/api/v1/reports/reason-code-summary/export",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == [
        "reason_code", "adjustments_count",
        "total_units_delta", "total_capital_at_cost",
    ]
    reasons = {row[0] for row in rows[1:]}
    assert "shrinkage" in reasons
    assert "damage" in reasons


def test_pdf_export_returns_pdf_bytes(client: TestClient, db, admin_headers):
    _seed_adj(db, sku="PDF-1", adjustment=-1, cost_price=10.0, reason_code="shrinkage")
    resp = client.get(
        "/api/v1/reports/reason-code-summary/export-pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")
    cd = resp.headers.get("content-disposition", "")
    assert "fulcrum-reason-code-summary" in cd


def test_csv_export_rejects_inverted_range(
    client: TestClient, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/reason-code-summary/export",
        params={"start_date": "2026-04-01", "end_date": "2026-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
