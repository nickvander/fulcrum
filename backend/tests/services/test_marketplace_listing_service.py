import pytest
from sqlalchemy.orm import Session
from src.services.marketplace_listing_service import marketplace_listing_service
from src.crud.crud_marketplace import marketplace as crud_marketplace
from src.crud.crud_product import product as crud_product
from src.schemas.marketplace import MarketplaceCreate
from src.schemas.product import ProductCreate
from src.models.marketplace import MarketplaceListing

from src.schemas.marketplace_credential import MarketplaceCredentialCreate
from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred

@pytest.mark.db
@pytest.mark.asyncio
async def test_import_listings_auto_mapping(db: Session, test_admin_user):
    # Setup: Create Marketplace and a Product with a specific SKU
    m_in = MarketplaceCreate(name="Amazon", api_base_url="https://api.amazon.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    # Create credentials
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token="test-token",
        refresh_token="test-refresh"
    )
    crud_cred.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    sku = "AMZ-TEST-SKU-123"
    p_in = ProductCreate(name="Existing Product", sku=sku, description="...", default_resale_price=10.0, cost_price=5.0)
    _db_p = crud_product.create(db, obj_in=p_in)  # noqa: F841
    
    # Let's just create a product that matches the stub's SKU for now.
    p_stub_in = ProductCreate(name="Stub Match", sku="STUB-SKU-001", description="...", default_resale_price=10.0, cost_price=5.0)
    db_p_stub = crud_product.create(db, obj_in=p_stub_in)
    
    stats = await marketplace_listing_service.import_marketplace_listings(db, db_m.id, test_admin_user.id)
    
    assert stats["synced"] >= 1
    # Check if a listing was created and linked to db_p_stub
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.marketplace_id == db_m.id,
        MarketplaceListing.product_id == db_p_stub.id
    ).first()
    assert listing is not None
    assert listing.external_listing_id == "AMZ-STUB-ASIN-001"

@pytest.mark.db
@pytest.mark.asyncio
async def test_import_listings_auto_create_shell(db: Session, test_admin_user):
    # Setup: Create Marketplace only, no matching product
    m_in = MarketplaceCreate(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    # Create credentials
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token="test-token",
        refresh_token="test-refresh"
    )
    crud_cred.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    stats = await marketplace_listing_service.import_marketplace_listings(db, db_m.id, test_admin_user.id)
    
    assert stats["created_product_shell"] >= 1
    # Check if a new product was created
    new_product = crud_product.get_by_sku(db, sku="STUB-SKU-001")
    assert new_product is not None
    assert "STUB-SKU-001" in new_product.sku
