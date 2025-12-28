import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.schemas.marketplace import MarketplaceCreate
from src.crud.crud_marketplace import marketplace as crud_marketplace

@pytest.mark.db
def test_create_credential_api(client: TestClient, db: Session, admin_headers: dict):
    # Setup: Create a marketplace
    m_in = MarketplaceCreate(name="Amazon", api_base_url="https://api.amazon.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    cred_data = {
        "marketplace_id": db_m.id,
        "access_token": "api-access-token",
        "refresh_token": "api-refresh-token",
        "token_type": "Bearer",
        "scopes": "all",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    
    response = client.post(
        "/api/v1/marketplace-credentials/",
        json=cred_data,
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["marketplace_id"] == db_m.id
    # Tokens should NOT be in the response
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "id" in data

@pytest.mark.db
def test_read_credentials_api(client: TestClient, db: Session, admin_headers: dict):
    m_in = MarketplaceCreate(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    # Create via API
    client.post(
        "/api/v1/marketplace-credentials/",
        json={"marketplace_id": db_m.id, "access_token": "t1", "refresh_token": "r1"},
        headers=admin_headers
    )
    
    response = client.get("/api/v1/marketplace-credentials/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(item["marketplace_id"] == db_m.id for item in data)

@pytest.mark.db
def test_delete_credential_api(client: TestClient, db: Session, admin_headers: dict):
    m_in = MarketplaceCreate(name="eBay", api_base_url="https://api.ebay.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    resp = client.post(
        "/api/v1/marketplace-credentials/",
        json={"marketplace_id": db_m.id, "access_token": "t2", "refresh_token": "r2"},
        headers=admin_headers
    )
    cred_id = resp.json()["id"]
    
    response = client.delete(f"/api/v1/marketplace-credentials/{cred_id}", headers=admin_headers)
    assert response.status_code == 200
    
    # Verify it's gone
    response = client.get(f"/api/v1/marketplace-credentials/{db_m.id}", headers=admin_headers)
    assert response.status_code == 404
