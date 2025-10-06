from fastapi.testclient import TestClient

def test_create_supplier(client: TestClient):
    """
    Test creating a supplier successfully.
    """
    response = client.post(
        "/suppliers/",
        json={
            "name": "Test Supplier",
            "contact_person": "John Doe",
            "email": "john.doe@testsupplier.com",
            "phone": "123-456-7890",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Supplier"
    assert data["email"] == "john.doe@testsupplier.com"
    assert "id" in data

def test_read_suppliers(client: TestClient):
    """
    Test reading a list of suppliers.
    """
    # Create a supplier first
    client.post(
        "/suppliers/",
        json={
            "name": "Another Supplier",
            "email": "contact@anothersupplier.com",
        },
    )

    response = client.get("/suppliers/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Another Supplier"
