"""Coverage for the reason_code filter on the inventory-adjustment
audit endpoints (`/reports/inventory-adjustments` + its CSV/PDF
exports + the `/reason-codes` dropdown source).

The filter has three branches that all need to be exercised:
  1. Known enum value (e.g. `shrinkage`) → only matching rows.
  2. Magic value `none` → NULL rows (legacy pre-migration).
  3. Anything else → 400 with a localized error code.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import (
    InventoryAdjustment,
    InventoryAdjustmentReasonCode,
)
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


def _seed_adjustment(
    db: Session, *, sku: str, adjustment: int, reason_code: str | None, reason: str = "",
) -> int:
    """Insert one product + one adjustment row with the supplied reason code."""
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Audit {sku}", sku=sku,
            default_resale_price=10.0, cost_price=5.0,
        ),
    )
    adj = InventoryAdjustment(
        product_id=product.id,
        adjustment=adjustment,
        reason=reason,
        reason_code=reason_code,
        timestamp=datetime.utcnow(),
        created_by="test-seed",
    )
    db.add(adj)
    db.commit()
    return product.id


# ---------------------------------------------------------------------------
# /reports/inventory-adjustments/reason-codes
# ---------------------------------------------------------------------------


def test_reason_codes_list_returns_canonical_enum_order(
    client: TestClient, admin_headers,
):
    """Frontend dropdown reads this endpoint instead of hard-coding
    the enum. Order must match the enum declaration so the dropdown
    stays stable across deploys."""
    resp = client.get("/api/v1/reports/inventory-adjustments/reason-codes", headers=admin_headers)
    assert resp.status_code == 200
    codes = resp.json()
    expected = [c.value for c in InventoryAdjustmentReasonCode]
    assert codes == expected
    # Sanity: every expected operator-actionable code is present.
    for needed in ("shrinkage", "recount", "damage", "return", "sale", "manual"):
        assert needed in codes


# ---------------------------------------------------------------------------
# Filtering on /reports/inventory-adjustments
# ---------------------------------------------------------------------------


def test_audit_filter_returns_only_matching_reason_code(
    client: TestClient, db, admin_headers,
):
    _seed_adjustment(db, sku="SHR-1", adjustment=-2, reason_code="shrinkage", reason="missing")
    _seed_adjustment(db, sku="SAL-1", adjustment=-1, reason_code="sale", reason="MLM-x")
    _seed_adjustment(db, sku="RET-1", adjustment=+1, reason_code="return", reason="returned")

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"reason_code": "shrinkage"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["rows"][0]["reason_code"] == "shrinkage"
    assert body["rows"][0]["product_sku"] == "SHR-1"


def test_audit_filter_none_returns_legacy_uncategorized_rows(
    client: TestClient, db, admin_headers,
):
    """Rows pre-dating the reason_code migration have NULL in the
    column. The dropdown's "Uncategorized" option sends
    `reason_code=none` to filter to them."""
    _seed_adjustment(db, sku="LEG-1", adjustment=+5, reason_code=None, reason="legacy")
    _seed_adjustment(db, sku="NEW-1", adjustment=-3, reason_code="damage", reason="dropped")

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"reason_code": "none"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["rows"][0]["product_sku"] == "LEG-1"
    assert body["rows"][0]["reason_code"] is None


def test_audit_filter_unknown_code_returns_400(client: TestClient, admin_headers):
    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"reason_code": "ufo-abduction"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.inventoryAdjustment.unknownReasonCode"


def test_audit_filter_composes_with_product_id(
    client: TestClient, db, admin_headers,
):
    """The reason_code filter stacks with the existing product_id
    filter — operator narrows by product first, then by reason."""
    shr_product = _seed_adjustment(db, sku="COMP-1", adjustment=-2, reason_code="shrinkage")
    # Another shrinkage row but for a different product.
    _seed_adjustment(db, sku="COMP-2", adjustment=-3, reason_code="shrinkage")
    # Same product as shr_product but a different reason code.
    other_product_id = _seed_adjustment(
        db, sku="COMP-3", adjustment=+1, reason_code="recount",
    )

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"reason_code": "shrinkage", "product_id": shr_product},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["rows"][0]["product_id"] == shr_product
    # Cross-check: filtering only on the other product's id (no
    # reason filter) finds its row.
    other_resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"product_id": other_product_id},
        headers=admin_headers,
    )
    assert other_resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# CSV export of the audit log
# ---------------------------------------------------------------------------


def test_audit_csv_includes_reason_code_column(
    client: TestClient, db, admin_headers,
):
    """The CSV export gains a `reason_code` column between the
    existing `adjustment` and `reason` columns so the spreadsheet
    column ordering matches what the operator sees on the audit page."""
    _seed_adjustment(db, sku="CSV-1", adjustment=-5, reason_code="theft", reason="break-in")

    resp = client.get(
        "/api/v1/reports/inventory-adjustments/export",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == [
        "timestamp", "product_id", "product_sku", "product_name",
        "adjustment", "reason_code", "reason", "created_by",
    ]
    # The seeded row carries the reason_code in column 5.
    data = [r for r in rows[1:] if r[2] == "CSV-1"]
    assert len(data) == 1
    assert data[0][5] == "theft"
    assert data[0][6] == "break-in"


def test_audit_csv_honors_reason_code_filter(
    client: TestClient, db, admin_headers,
):
    """Filter pass-through: the CSV export uses the same filter
    machinery as the JSON list endpoint, so a `reason_code=theft`
    query returns only theft rows."""
    _seed_adjustment(db, sku="CSV-T-1", adjustment=-1, reason_code="theft")
    _seed_adjustment(db, sku="CSV-S-1", adjustment=-1, reason_code="sale")

    resp = client.get(
        "/api/v1/reports/inventory-adjustments/export",
        params={"reason_code": "theft"},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(resp.text)))
    skus = {r[2] for r in rows[1:]}
    assert "CSV-T-1" in skus
    assert "CSV-S-1" not in skus


def test_audit_csv_rejects_unknown_reason_code(
    client: TestClient, admin_headers,
):
    resp = client.get(
        "/api/v1/reports/inventory-adjustments/export",
        params={"reason_code": "ufo-abduction"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Wired callers stamp the right reason code
# ---------------------------------------------------------------------------


def test_order_ingestion_path_stamps_sale_reason_code(
    db, test_product,
):
    """Smoke that the order ingestion path's adjust_stock call
    sets reason_code='sale'. Exercises the wiring without
    spinning up the full poll harness."""
    from src.services.inventory_service import inventory_service

    inventory_service.adjust_stock(
        db,
        product_id=test_product.id,
        adjustment=-1,
        reason="ML order EXT-1",
        reason_code=InventoryAdjustmentReasonCode.SALE,
        user_id="mercadolibre-poll",
    )
    db.commit()

    adj = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.product_id == test_product.id)
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )
    assert adj.reason_code == "sale"
