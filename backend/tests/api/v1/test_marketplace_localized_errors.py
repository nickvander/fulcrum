"""Localized error wire-shape tests for marketplace.py."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud.crud_marketplace import marketplace as crud_marketplace
from src.models.marketplace import MarketplaceListing as ModelListing
from src.schemas.marketplace import MarketplaceCreate


@pytest.mark.db
def test_read_marketplace_summary_for_missing_id_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """GET /marketplace/{id}/summary for a non-existent marketplace reuses the
    marketplaceCredentials.marketplaceNotFound code (the shared 'marketplace
    not found' wire shape used across the marketplace flow)."""
    response = client.get(
        "/api/v1/marketplace/999999/summary",
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
def test_sync_missing_listing_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """POST /marketplace/listings/{id}/sync when the listing does not exist."""
    response = client.post(
        "/api/v1/marketplace/listings/999999/sync",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Listing not found",
        "code": "apiErrors.marketplace.listingNotFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_sync_listing_without_credentials_returns_localized_payload(
    client: TestClient, admin_headers: dict, db: Session
):
    """POST /marketplace/listings/{id}/sync when the listing exists but the
    current user has no marketplace credentials connected."""
    m = crud_marketplace.create(
        db,
        obj_in=MarketplaceCreate(
            name="MercadoLibre", api_base_url="https://api.mercadolibre.com"
        ),
    )
    db.flush()
    listing = ModelListing(
        marketplace_id=m.id,
        external_listing_id="EXT-1",
        status="ACTIVE",
        sync_status="IN_SYNC",
    )
    db.add(listing)
    db.commit()

    response = client.post(
        f"/api/v1/marketplace/listings/{listing.id}/sync",
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "No credentials found for this marketplace",
        "code": "apiErrors.marketplace.noCredentialsForMarketplace",
        "params": {"marketplaceId": m.id},
    }
