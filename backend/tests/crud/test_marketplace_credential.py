import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.crud.crud_marketplace_credential import marketplace_credential
from src.crud.crud_marketplace import marketplace as crud_marketplace
from src.schemas.marketplace_credential import MarketplaceCredentialCreate, MarketplaceCredentialUpdate
from src.schemas.marketplace import MarketplaceCreate
from src.models.user import User

@pytest.mark.db
def test_create_marketplace_credential(db: Session, test_admin_user: User):
    # Setup: Create a marketplace
    m_in = MarketplaceCreate(name="Amazon", api_base_url="https://api.amazon.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    # Test Create
    access_token = "plain-access-token"
    refresh_token = "plain-refresh-token"
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        scopes="all",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    db_obj = marketplace_credential.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    assert db_obj.marketplace_id == db_m.id
    assert db_obj.user_id == test_admin_user.id
    assert db_obj.access_token != access_token  # Should be encrypted
    assert db_obj.refresh_token != refresh_token  # Should be encrypted
    
    # Test Decryption
    assert marketplace_credential.get_decrypted_access_token(db_obj) == access_token
    assert marketplace_credential.get_decrypted_refresh_token(db_obj) == refresh_token

@pytest.mark.db
def test_update_marketplace_credential(db: Session, test_admin_user: User):
    m_in = MarketplaceCreate(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db_m = crud_marketplace.create(db, obj_in=m_in)
    
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token="old-token",
        refresh_token="old-refresh",
    )
    db_obj = marketplace_credential.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    # Update
    new_access = "new-access-token"
    update_in = MarketplaceCredentialUpdate(access_token=new_access)
    updated_obj = marketplace_credential.update_with_encryption(db, db_obj=db_obj, obj_in=update_in)
    
    assert marketplace_credential.get_decrypted_access_token(updated_obj) == new_access
    assert marketplace_credential.get_decrypted_refresh_token(updated_obj) == "old-refresh"
