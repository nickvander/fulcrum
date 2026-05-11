import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from src.services.marketplace_service import marketplace_service
from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
from src.schemas.marketplace_credential import MarketplaceCredentialCreate
from src.schemas.marketplace import MarketplaceCreate
from src.crud.crud_marketplace import marketplace as crud_m

@pytest.mark.db
@pytest.mark.anyio
async def test_get_valid_access_token_no_refresh(db: Session, test_admin_user):
    # Setup: Create marketplace and credential that is NOT expired
    m_in = MarketplaceCreate(name="Amazon", api_base_url="https://api.amazon.com")
    db_m = crud_m.create(db, obj_in=m_in)
    
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token="valid-token",
        refresh_token="valid-refresh",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_cred = crud_cred.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    token = await marketplace_service.get_valid_access_token(db, db_cred.id)
    assert token == "valid-token"

@pytest.mark.db
@pytest.mark.anyio
async def test_get_valid_access_token_with_refresh(db: Session, test_admin_user):
    # Setup: Create marketplace and credential that IS expired
    m_in = MarketplaceCreate(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db_m = crud_m.create(db, obj_in=m_in)
    
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=db_m.id,
        access_token="expired-token",
        refresh_token="valid-refresh",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    db_cred = crud_cred.create_with_owner(db, obj_in=cred_in, user_id=test_admin_user.id)
    
    # Mock connector refresh
    mock_new_tokens = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600
    }
    
    with patch("src.services.marketplace_service.MarketplaceService.get_connector") as mock_get:
        mock_connector = AsyncMock()
        mock_connector.refresh_token.return_value = mock_new_tokens
        mock_get.return_value = mock_connector
        
        token = await marketplace_service.get_valid_access_token(db, db_cred.id)
        assert token == "new-access-token"
        
        # Verify DB was updated
        db.refresh(db_cred)
        assert crud_cred.get_decrypted_access_token(db_cred) == "new-access-token"
        assert crud_cred.get_decrypted_refresh_token(db_cred) == "new-refresh-token"
        assert db_cred.expires_at > datetime.now(timezone.utc)
