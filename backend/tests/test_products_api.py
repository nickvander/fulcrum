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

def test_read_products(client: TestClient, test_product: Product):
    """
    Test reading a list of products.
    """
    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == test_product.name
