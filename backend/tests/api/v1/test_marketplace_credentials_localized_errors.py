"""Localized error wire-shape tests for marketplace_credentials.py."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.schemas.marketplace import MarketplaceCreate
from src.crud.crud_marketplace import marketplace as crud_marketplace


@pytest.mark.db
def test_get_credentials_for_missing_marketplace_returns_localized_payload(
    client: TestClient, admin_headers: dict, db: Session
):
    """GET /{marketplace_id} when no credential is connected for that marketplace.
    The endpoint needs the marketplace to exist (otherwise the upstream
    get_by_marketplace returns None for a different reason), so we seed one
    first then query its credentials."""
    m = crud_marketplace.create(
        db,
        obj_in=MarketplaceCreate(name="EmptyTest", api_base_url="https://example.com"),
    )
    db.commit()

    response = client.get(
        f"/api/v1/marketplace-credentials/{m.id}",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Credentials not found for this marketplace",
        "code": "apiErrors.marketplaceCredentials.notFoundForMarketplace",
        "params": {"marketplaceId": m.id},
    }


@pytest.mark.db
def test_delete_missing_credential_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """DELETE /{id} when no such credential exists."""
    response = client.delete(
        "/api/v1/marketplace-credentials/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Credential not found",
        "code": "apiErrors.marketplaceCredentials.notFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_authorize_unsupported_marketplace_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """GET /by-name/{name}/authorize for a name not in the support list."""
    response = client.get(
        "/api/v1/marketplace-credentials/by-name/etsy/authorize",
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.marketplaceCredentials.unsupportedMarketplace"
    assert body["params"] == {"name": "etsy"}


@pytest.mark.db
def test_authorize_missing_marketplace_id_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """GET /{marketplace_id}/authorize when no marketplace exists with that id."""
    response = client.get(
        "/api/v1/marketplace-credentials/999999/authorize",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Marketplace not found",
        "code": "apiErrors.marketplaceCredentials.marketplaceNotFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_callback_for_missing_marketplace_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """GET /{marketplace_id}/callback hits the same marketplace-not-found 404 path."""
    response = client.get(
        "/api/v1/marketplace-credentials/999999/callback?code=fake-oauth-code",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "apiErrors.marketplaceCredentials.marketplaceNotFound"


@pytest.mark.db
def test_callback_with_bad_oauth_code_returns_localized_tokenExchangeFailed(
    client: TestClient, admin_headers: dict, db: Session
):
    """A real marketplace + an invalid OAuth code triggers the connector to
    raise; the endpoint wraps that as tokenExchangeFailed with the underlying
    error as the `reason` param so the UI can surface it."""
    m_in = MarketplaceCreate(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    m = crud_marketplace.create(db, obj_in=m_in)
    db.commit()

    response = client.get(
        f"/api/v1/marketplace-credentials/{m.id}/callback?code=definitely-not-real",
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.marketplaceCredentials.tokenExchangeFailed"
    assert "reason" in body["params"]
    assert isinstance(body["params"]["reason"], str) and len(body["params"]["reason"]) > 0
