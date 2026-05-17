"""Tests for the LocalizedHTTPException + exception handler wire shape.

Covers two layers:

1. Unit: the exception itself stores code/params/detail correctly.
2. Integration: a 404 from /api/v1/products/{id} comes back as the new
   {detail, code, params} JSON, and a 409 from create_product round-trips
   params (the SKU). This is the contract the frontend translateApiError
   helper depends on.
"""
import pytest
from fastapi.testclient import TestClient

from src.core.errors import LocalizedHTTPException


def test_localized_exception_stores_code_params_and_detail():
    exc = LocalizedHTTPException(
        status_code=404,
        code="apiErrors.product.notFound",
        params={"id": 7},
        detail="Product not found",
    )
    assert exc.status_code == 404
    assert exc.code == "apiErrors.product.notFound"
    assert exc.params == {"id": 7}
    assert exc.detail == "Product not found"


def test_localized_exception_defaults_detail_to_code_when_omitted():
    exc = LocalizedHTTPException(status_code=500, code="apiErrors.internal")
    assert exc.detail == "apiErrors.internal"
    assert exc.params == {}


@pytest.mark.db
def test_product_not_found_returns_localized_payload(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/products/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "The product with this ID does not exist in the system.",
        "code": "apiErrors.product.notFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_create_product_with_duplicate_sku_returns_localized_payload(
    client: TestClient, admin_headers: dict, test_product
):
    """Duplicate SKU on create should return the sku in params — the frontend
    needs it to render the Spanish copy "Ya existe un producto con el SKU {sku}"."""
    response = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "name": "Duplicate attempt",
            "sku": test_product.sku,
            "default_resale_price": 1.0,
            "cost_price": 0.5,
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "apiErrors.product.skuExists"
    assert body["params"] == {"sku": test_product.sku}
    assert body["detail"] == "A product with this SKU already exists."
