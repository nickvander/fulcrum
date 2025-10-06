from fastapi.testclient import TestClient
from src.models.product import Product

def test_create_product(client: TestClient):
    """
    Test creating a product successfully.
    """
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product",
            "description": "A product for testing",
            "sku": "TESTSKU123",
            "default_resale_price": 19.99,
            "cost_price": 10.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["sku"] == "TESTSKU123"
    assert "id" in data

import pytest
from sqlalchemy.orm import Session

def test_search_products(client: TestClient, db: Session, test_product: Product):
    """
    Test semantic search for products.
    """
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Vector search test requires PostgreSQL")

    # The dummy AI service will return a random embedding, but for a single product
    # the search should still return that product.
    response = client.get(f"/api/v1/products/search/?q={test_product.name}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # The exact order isn't guaranteed with random embeddings,
    # so we just check if the product is in the results.
    assert test_product.name in [p["name"] for p in data]
