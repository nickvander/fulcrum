import pytest
import os

import uuid
from sqlalchemy.orm import Session
from src.crud import crud_marketplace, crud_marketplace_credential, crud_product
from src.schemas import marketplace as marketplace_schema
from src.schemas import marketplace_credential as credential_schema
from src.schemas import product as product_schema
from src.services.marketplace_listing_service import marketplace_listing_service
from src.config import settings

@pytest.fixture(scope="module")
def amazon_creds():
    client_id = os.environ.get("AMAZON_CLIENT_ID")
    client_secret = os.environ.get("AMAZON_CLIENT_SECRET")
    refresh_token = os.environ.get("AMAZON_REFRESH_TOKEN") # Need a valid refresh token for sandbox
    
    if not (client_id and client_secret and refresh_token):
        print("\n\n[!] SKIPPING LIVE TEST: Amazon credentials missing.")
        print("    Requires: AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET, AMAZON_REFRESH_TOKEN")
        print("    See 'work/current/63-marketplace-credential-setup-guide.md' for setup instructions.\n")
        pytest.skip("AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET, or AMAZON_REFRESH_TOKEN not set")
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }

@pytest.mark.integration
@pytest.mark.integration_amazon
@pytest.mark.asyncio
async def test_amazon_sync_lifecycle(db: Session, amazon_creds, test_admin_user):
    # 1. Setup Marketplace with Sandbox config
    # ----------------------------------------
    # Force Sandbox Mode
    settings.AMAZON_SANDBOX = True
    
    mp = crud_marketplace.marketplace.get_by_name(db, name="Amazon Sandbox")
    if not mp:
        mp = crud_marketplace.marketplace.create(db, obj_in=marketplace_schema.MarketplaceCreate(
            name="Amazon Sandbox",
            api_base_url="https://sandbox.sellingpartnerapi-na.amazon.com"
        ))
    
    # 2. Setup Credentials
    # --------------------
    cred_in = credential_schema.MarketplaceCredentialCreate(
        marketplace_id=mp.id,
        access_token="mock_initial_access_token", # Will be refreshed
        refresh_token=amazon_creds["refresh_token"],
        expires_at=None
    )
    
    # Clean old creds
    cred = crud_marketplace_credential.marketplace_credential.get_by_marketplace(db, user_id=test_admin_user.id, marketplace_id=mp.id)
    if cred:
        crud_marketplace_credential.marketplace_credential.remove(db, id=cred.id)
    
    cred = crud_marketplace_credential.marketplace_credential.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    # 3. Create Product
    # -----------------
    sku = f"TEST-AMZ-{uuid.uuid4().hex[:8]}"
    print(f"Creating Product {sku} in Fulcrum...")
    
    product_in = product_schema.ProductCreate(
        name=f"Amazon Integration Test Item {sku}",
        description="Amazon Sandbox Test Item",
        sku=sku,
        price=29.99,
        stock_quantity=50,
        weight_kg=0.5
    )
    product = crud_product.product.create(db, obj_in=product_in)
    
    # 4. Publish / Sync
    # -----------------
    # For Amazon, "Publish" usually means "Put Listings Item".
    # In Sandbox, we expect 200 OK.
    
    try:
        print("Publishing to Amazon Sandbox...")
        listing = await marketplace_listing_service.publish_to_marketplace(
            db, 
            product_id=product.id, 
            marketplace_id=mp.id, 
            user_id=test_admin_user.id
        )
        
        print(f"Published! External ID (ASIN stub): {listing.external_listing_id}")
        assert listing.status == "SYNCED"
        
        # 5. Inventory Update
        # -------------------
        # Verify separate inventory sync call
        print("Updating Inventory...")
        success = await marketplace_listing_service.sync_inventory(
            db, 
            listing_id=listing.id, 
            user_id=test_admin_user.id
        )
        assert success is True
        print("Inventory Sync Successful")
        
    except Exception as e:
        pytest.fail(f"Amazon Integration Test Failed: {str(e)}")
        
    finally:
        # Cleanup
        if product:
            db.delete(product)
        if cred:
            db.delete(cred)
        db.commit()
