"""CSV + PDF export for the inventory-snapshot report.

Distinct from low-stock: this lists every product with its on-hand qty
and computed cost / retail value, the quarter-end accounting view.
Bundles are excluded.
"""
import csv
import io
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem
from src.models.product import Product


@pytest.fixture
def seeded_products(db: Session) -> dict[str, Product]:
    p_widget = Product(
        name="Widget Pro",
        sku="WIDG-001",
        category="Tools",
        default_resale_price=50.00,
        cost_price=20.00,
        is_bundle=False,
    )
    p_zero_stock = Product(
        name="Out of Stock Item",
        sku="OOS-1",
        category="Tools",
        default_resale_price=10.00,
        cost_price=4.00,
        is_bundle=False,
    )
    p_bundle = Product(
        name="Bundle Should Be Excluded",
        sku="BUNDLE-1",
        default_resale_price=200.00,
        cost_price=120.00,
        is_bundle=True,
    )
    db.add_all([p_widget, p_zero_stock, p_bundle])
    db.flush()
    db.add(InventoryItem(product_id=p_widget.id, quantity=10, location="default"))
    db.commit()
    return {"widget": p_widget, "oos": p_zero_stock, "bundle": p_bundle}


@pytest.mark.db
def test_inventory_snapshot_csv_includes_value_columns_and_excludes_bundles(
    client: TestClient, admin_headers: dict, seeded_products: dict[str, Product]
):
    response = client.get("/api/v1/reports/inventory-snapshot/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-inventory-snapshot-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "product_id", "product_sku", "product_name", "category",
        "on_hand", "cost_price", "inventory_value_cost",
        "default_resale_price", "inventory_value_retail",
        "days_of_inventory",
    ]
    body_by_sku = {row[1]: row for row in rows[1:]}

    # Bundle excluded
    assert "BUNDLE-1" not in body_by_sku
    # Both non-bundle products listed
    assert "WIDG-001" in body_by_sku
    assert "OOS-1" in body_by_sku

    widget = body_by_sku["WIDG-001"]
    assert widget[4] == "10"                  # on_hand
    assert widget[5] == "USD 20.00"           # cost_price
    assert widget[6] == "USD 200.00"          # value at cost (10 * 20)
    assert widget[7] == "USD 50.00"           # retail price
    assert widget[8] == "USD 500.00"          # value at retail (10 * 50)

    # Zero-stock row still shows up but values are zero
    oos = body_by_sku["OOS-1"]
    assert oos[4] == "0"
    assert oos[6] == "USD 0.00"
    assert oos[8] == "USD 0.00"


@pytest.mark.db
def test_inventory_snapshot_csv_with_no_products_returns_header_only(
    client: TestClient, admin_headers: dict, db: Session
):
    response = client.get("/api/v1/reports/inventory-snapshot/export", headers=admin_headers)
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0][0] == "product_id"


@pytest.mark.db
def test_inventory_snapshot_pdf_renders(
    client: TestClient, admin_headers: dict, seeded_products: dict[str, Product]
):
    response = client.get(
        "/api/v1/reports/inventory-snapshot/export-pdf", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    body = response.content
    assert body.startswith(b"%PDF-")
    assert body.rstrip().endswith(b"%%EOF")
