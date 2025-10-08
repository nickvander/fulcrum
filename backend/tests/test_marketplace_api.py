from fastapi.testclient import TestClient

def test_create_marketplace(client: TestClient):
    """
    Test creating a marketplace successfully.
    """
    response = client.post(
        "/api/v1/marketplace/",
        json={"name": "Test Marketplace", "api_base_url": "https://api.test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Marketplace"
    assert "id" in data

def test_read_marketplaces(client: TestClient):
    """
    Test reading a list of marketplaces.
    """
    # Create a marketplace first
    client.post(
        "/api/v1/marketplace/",
        json={"name": "Another Marketplace"},
    )

    response = client.get("/api/v1/marketplace/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "Another Marketplace" in [m["name"] for m in data]
