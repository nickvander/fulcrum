"""Test that the marketplace summary endpoint surfaces the
needs_reauthorization flag from the credential so the frontend
marketplace cards can render a reauth chip without a second round trip."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import models
from src.schemas.marketplace import MarketplaceCreate
from src.schemas.marketplace_credential import MarketplaceCredentialCreate
from src.crud.crud_marketplace import marketplace as crud_marketplace
from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred


@pytest.mark.db
def test_summary_returns_needs_reauthorization_false_for_healthy_credential(
    client: TestClient, admin_headers: dict, db: Session, test_admin_user: models.User
):
    m = crud_marketplace.create(
        db,
        obj_in=MarketplaceCreate(name="MercadoLibre-Healthy", api_base_url="https://api.mercadolibre.com"),
    )
    crud_cred.create_with_owner(
        db,
        obj_in=MarketplaceCredentialCreate(
            marketplace_id=m.id, access_token="t", refresh_token="r",
        ),
        user_id=test_admin_user.id,
    )
    db.commit()

    response = client.get(f"/api/v1/marketplace/{m.id}/summary", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["credential_connected"] is True
    assert body["needs_reauthorization"] is False
    assert body["reauthorization_reason"] is None


@pytest.mark.db
def test_summary_returns_needs_reauthorization_true_when_credential_marked(
    client: TestClient, admin_headers: dict, db: Session, test_admin_user: models.User
):
    """After get_valid_access_token marks a credential needs_reauthorization
    (e.g. invalid_grant), the summary surfaces both the flag and the
    last_refresh_error so the UI can show the reason inline."""
    m = crud_marketplace.create(
        db,
        obj_in=MarketplaceCreate(name="MercadoLibre-Stale", api_base_url="https://api.mercadolibre.com"),
    )
    cred = crud_cred.create_with_owner(
        db,
        obj_in=MarketplaceCredentialCreate(
            marketplace_id=m.id, access_token="t", refresh_token="r",
        ),
        user_id=test_admin_user.id,
    )
    cred.needs_reauthorization = True
    cred.last_refresh_error = "invalid_grant (refresh token revoked)"
    db.commit()

    response = client.get(f"/api/v1/marketplace/{m.id}/summary", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["credential_connected"] is True
    assert body["needs_reauthorization"] is True
    assert body["reauthorization_reason"] == "invalid_grant (refresh token revoked)"


@pytest.mark.db
def test_summary_returns_needs_reauthorization_false_when_no_credential(
    client: TestClient, admin_headers: dict, db: Session,
):
    """A marketplace with no credential at all isn't "needs reauth" —
    it's "not connected". The flag must be false to keep the UI's
    branching simple."""
    m = crud_marketplace.create(
        db,
        obj_in=MarketplaceCreate(name="Amazon-Unconnected", api_base_url="https://sellingpartnerapi-na.amazon.com"),
    )
    db.commit()

    response = client.get(f"/api/v1/marketplace/{m.id}/summary", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["credential_connected"] is False
    assert body["needs_reauthorization"] is False
    assert body["reauthorization_reason"] is None
