"""Test CSV export of the low-stock report.

The endpoint streams the same data as the JSON `/reports/low-stock`,
just in a spreadsheet-friendly format. Verifies:
- 200 + correct Content-Type + filename header (date-stamped)
- Header row + one data row per product
- Empty fields are emitted as empty strings, not the literal "None"
"""
import csv
import io
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem
from src.models.product import Product


@pytest.mark.db
def test_low_stock_export_returns_csv_with_correct_headers(
    client: TestClient, admin_headers: dict, db: Session
):
    p_strict = Product(
        name="Stout (strict reorder)",
        sku="STOUT-1",
        default_resale_price=12.0,
        cost_price=4.0,
        is_bundle=False,
        reorder_point=20,
        reorder_quantity=50,
    )
    p_loose = Product(
        name="Saison (auto reorder)",
        sku="SAISON-1",
        default_resale_price=14.0,
        cost_price=5.0,
        is_bundle=False,
    )
    db.add_all([p_strict, p_loose])
    db.flush()
    db.add_all([
        InventoryItem(product_id=p_strict.id, quantity=0, location="default"),
        InventoryItem(product_id=p_loose.id, quantity=2, location="default"),
    ])
    db.commit()

    response = client.get("/api/v1/reports/low-stock/export", headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    cd = response.headers.get("content-disposition", "")
    assert re.search(r'filename="fulcrum-low-stock-\d{4}-\d{2}-\d{2}\.csv"', cd)

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert rows[0] == [
        "product_id", "product_sku", "product_name",
        "severity", "on_hand", "threshold",
        "reorder_point", "reorder_quantity", "suggested_reorder_qty",
        "daily_velocity", "days_of_inventory",
    ]

    body_by_sku = {row[1]: row for row in rows[1:]}
    assert "STOUT-1" in body_by_sku
    assert "SAISON-1" in body_by_sku

    stout = body_by_sku["STOUT-1"]
    assert stout[3] == "critical"
    assert stout[5] == "20"
    assert stout[6] == "20"
    assert stout[7] == "50"

    saison = body_by_sku["SAISON-1"]
    assert saison[6] == ""
    assert saison[7] == ""


@pytest.mark.db
def test_low_stock_export_with_no_low_stock_returns_header_only(
    client: TestClient, admin_headers: dict, db: Session
):
    """No low-stock products → CSV with the header row but no data rows.
    Still 200 (an empty inventory report isn't an error)."""
    response = client.get("/api/v1/reports/low-stock/export", headers=admin_headers)

    assert response.status_code == 200
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0][0] == "product_id"


@pytest.mark.db
def test_low_stock_export_pdf_streams_a_real_pdf_with_data(
    client: TestClient, admin_headers: dict, db: Session
):
    """PDF export should return a valid PDF byte stream with the date-stamped
    filename. We verify the magic bytes + that the response body is large
    enough to contain real content (an empty PDF is ~700 bytes; a PDF with
    a row of data is meaningfully bigger). We don't crack the deflate
    streams to verify the SKU text — that's covered by the integration
    walkthrough."""
    p_strict = Product(
        name="Stout (strict reorder)",
        sku="STOUT-PDF-1",
        default_resale_price=12.0,
        cost_price=4.0,
        is_bundle=False,
        reorder_point=20,
        reorder_quantity=50,
    )
    db.add(p_strict)
    db.flush()
    db.add(InventoryItem(product_id=p_strict.id, quantity=0, location="default"))
    db.commit()

    response = client.get("/api/v1/reports/low-stock/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")

    cd = response.headers.get("content-disposition", "")
    assert re.search(r'filename="fulcrum-low-stock-\d{4}-\d{2}-\d{2}\.pdf"', cd)

    body = response.content
    assert body.startswith(b"%PDF-"), "Response is not a PDF"
    assert body.rstrip().endswith(b"%%EOF"), "Response is not a complete PDF"
    assert len(body) > 1500, "PDF looks too small to contain a data row"


@pytest.mark.db
def test_low_stock_export_pdf_empty_report_still_renders(
    client: TestClient, admin_headers: dict, db: Session
):
    """No low-stock products → PDF still renders with the empty-state line.
    Same convention as the CSV export."""
    response = client.get("/api/v1/reports/low-stock/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
