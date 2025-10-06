from fastapi.testclient import TestClient

def test_create_product(client: TestClient):
    """
    Test creating a product successfully.
    """
    response = client.post(
        "/products/",
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

def test_read_products(client: TestClient):
    """
    Test reading a list of products.
    """
    # Create a product first
    client.post(
        "/products/",
        json={
            "name": "Test Product 2",
            "description": "Another test product",
            "sku": "TESTSKU456",
            "default_resale_price": 29.99,
            "cost_price": 15.0,
        },
    )

    response = client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Test Product 2"
