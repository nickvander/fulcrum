from fastapi.testclient import TestClient
from src.models.product import Product
import pytest
from sqlalchemy.orm import Session

from unittest.mock import patch

def test_create_product(client: TestClient):
    """
    Test creating a product successfully and that the embedding task is called.
    """
    with patch("src.tasks.generate_product_embedding.delay") as mock_delay:
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
        mock_delay.assert_called_once_with(data["id"])

def test_create_product_duplicate_sku(client: TestClient, test_product: Product):
    """
    Test creating a product with a duplicate SKU fails.
    """
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Another Product",
            "description": "A product with a duplicate SKU",
            "sku": test_product.sku, # Use the same SKU as the fixture
        },
    )
    assert response.status_code == 409
    assert "Product with this SKU already exists" in response.text

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
    
    def test_update_product(client: TestClient, test_product: Product):
        """
        Test updating a product successfully and that the embedding task is called.
        """
        with patch("src.tasks.generate_product_embedding.delay") as mock_delay:
            updated_name = "Updated Test Product"
            response = client.put(
                f"/api/v1/products/{test_product.id}",
                json={"name": updated_name},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == updated_name
            assert data["id"] == test_product.id
            mock_delay.assert_called_once_with(test_product.id)
    