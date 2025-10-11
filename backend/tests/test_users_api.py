import pytest
from fastapi.testclient import TestClient

@pytest.mark.db
def test_create_user(client: TestClient):
    response = client.post(
        "/api/v1/users/",
        json={"email": "test-create-user-7@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test-create-user-7@example.com"
    assert "id" in data
    assert "password" not in data  # Ensure password is not returned