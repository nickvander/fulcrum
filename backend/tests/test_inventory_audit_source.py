"""Coverage for the structured `source` filter on the inventory-adjustment
audit endpoints (`/reports/inventory-adjustments` + CSV export + the
`/sources` dropdown source) — the P2-8 follow-up.

Mirrors the reason_code filter's branches:
  1. Known source value (e.g. `stock_transfer`) → only matching rows.
  2. Magic value `none` → rows with NULL source (legacy / manual).
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
from src.models.inventory import InventoryAdjustment, InventoryAdjustmentSource
from src.schemas.product import ProductCreate

pytestmark = pytest.mark.db


def _seed(db: Session, *, sku: str, source: str | None, source_id: int | None) -> int:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name=f"Src {sku}", sku=sku, default_resale_price=10.0, cost_price=5.0),
    )
    db.add(
        InventoryAdjustment(
            product_id=product.id,
            adjustment=3,
            reason="seed",
            source=source,
            source_id=source_id,
            timestamp=datetime.utcnow(),
            created_by="test-seed",
        )
    )
    db.commit()
    return product.id


def test_sources_list_returns_canonical_enum_order(client: TestClient, admin_headers):
    resp = client.get("/api/v1/reports/inventory-adjustments/sources", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == [s.value for s in InventoryAdjustmentSource]


def test_filter_by_known_source(client: TestClient, db: Session, admin_headers):
    pid_transfer = _seed(db, sku="SRC-T", source="stock_transfer", source_id=11)
    _seed(db, sku="SRC-O", source="sales_order", source_id=22)

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"source": "stock_transfer"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    pids = {r["product_id"] for r in body["rows"]}
    assert pid_transfer in pids
    assert all(r["source"] == "stock_transfer" for r in body["rows"])
    # source_id is surfaced on the row.
    row = next(r for r in body["rows"] if r["product_id"] == pid_transfer)
    assert row["source_id"] == 11


def test_filter_none_returns_only_structureless_rows(client: TestClient, db: Session, admin_headers):
    pid_manual = _seed(db, sku="SRC-M", source=None, source_id=None)
    _seed(db, sku="SRC-B", source="bundle_assembly", source_id=5)

    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"source": "none"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert all(r["source"] is None for r in rows)
    assert pid_manual in {r["product_id"] for r in rows}


def test_unknown_source_is_rejected(client: TestClient, admin_headers):
    resp = client.get(
        "/api/v1/reports/inventory-adjustments",
        params={"source": "not_a_real_source"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_csv_export_has_source_column_and_respects_filter(client: TestClient, db: Session, admin_headers):
    _seed(db, sku="SRC-CSV-T", source="stock_transfer", source_id=7)
    _seed(db, sku="SRC-CSV-O", source="sales_order", source_id=8)

    resp = client.get(
        "/api/v1/reports/inventory-adjustments/export",
        params={"source": "stock_transfer"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.content.decode("utf-8")))
    rows = list(reader)
    # CSV headers are the column keys (not the display labels).
    assert "source" in reader.fieldnames
    # Only the stock_transfer row is in the filtered export.
    assert rows, "expected at least one exported row"
    assert all(r["source"] == "stock_transfer" for r in rows)
