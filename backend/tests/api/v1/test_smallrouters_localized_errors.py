"""Localized error wire-shape tests for the small-router migration batch.

Covers one round-trip per migrated raise site across:
- bulk_users.py (3 sites)
- sales_orders.py (1 site)
- stock_transfers.py (1 site)
- settings.py (1 site)
- suppliers.py (1 site)
"""
import io

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# bulk_users.py
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_bulk_import_non_csv_returns_localized_onlyCsvAllowed(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/bulk-users/bulk-import",
        headers=admin_headers,
        files={"file": ("users.txt", io.BytesIO(b"not a csv"), "text/plain")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Only CSV files are allowed",
        "code": "apiErrors.bulkUsers.onlyCsvAllowed",
        "params": {},
    }


@pytest.mark.db
def test_bulk_import_non_utf8_returns_localized_invalidEncoding(
    client: TestClient, admin_headers: dict
):
    # Latin-1 byte that is invalid UTF-8 (0xff)
    bad_bytes = b"email,first_name,last_name\n\xff\xfe@x.com,Foo,Bar\n"
    response = client.post(
        "/api/v1/bulk-users/bulk-import",
        headers=admin_headers,
        files={"file": ("users.csv", io.BytesIO(bad_bytes), "text/csv")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Invalid file encoding. Please upload a UTF-8 encoded CSV.",
        "code": "apiErrors.bulkUsers.invalidEncoding",
        "params": {},
    }


@pytest.mark.db
def test_bulk_import_missing_columns_returns_localized_missingRequiredColumns(
    client: TestClient, admin_headers: dict
):
    # Only one of the three required columns present.
    csv_bytes = b"email\nfoo@example.com\n"
    response = client.post(
        "/api/v1/bulk-users/bulk-import",
        headers=admin_headers,
        files={"file": ("users.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.bulkUsers.missingRequiredColumns"
    assert body["detail"].startswith("CSV must contain the following columns: ")
    assert "columns" in body["params"]


# ---------------------------------------------------------------------------
# sales_orders.py
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_missing_sales_order_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/sales-orders/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Sales order not found",
        "code": "apiErrors.salesOrder.notFound",
        "params": {"id": 999999},
    }


# ---------------------------------------------------------------------------
# stock_transfers.py
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_missing_stock_transfer_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/stock-transfers/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Stock transfer not found",
        "code": "apiErrors.stockTransfer.notFound",
        "params": {"id": 999999},
    }


# ---------------------------------------------------------------------------
# settings.py
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_save_unknown_marketplace_returns_localized_unknownMarketplace(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/settings/marketplace",
        headers=admin_headers,
        json={
            "marketplace": "bogus-marketplace",
            "client_id": "x",
            "client_secret": "y",
            "redirect_uri": "https://example.com/cb",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Unknown marketplace",
        "code": "apiErrors.setting.unknownMarketplace",
        "params": {"marketplace": "bogus-marketplace"},
    }


# ---------------------------------------------------------------------------
# suppliers.py
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_missing_supplier_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/suppliers/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Supplier not found",
        "code": "apiErrors.supplier.notFound",
        "params": {"id": 999999},
    }
