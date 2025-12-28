"""
Settings API endpoints for managing marketplace credentials and other configuration.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.api import dependencies
from src.api.dependencies import get_db
from src.models.user import User

router = APIRouter()


class MarketplaceSettingsInput(BaseModel):
    marketplace: str
    client_id: str
    client_secret: str
    redirect_uri: str


@router.get("/marketplace")
def get_marketplace_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Get marketplace settings for the current user.
    Secrets are masked.
    """
    from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
    
    credentials = crud_cred.get_multi_by_owner(db, user_id=current_user.id)


    
    settings: Dict[str, Any] = {}
    for cred in credentials:
        # Get marketplace name
        from src.crud.crud_marketplace import marketplace as crud_m
        m = crud_m.get(db, id=cred.marketplace_id)
        if m:
            name = m.name.lower()
            settings[name] = {
                "client_id": "***configured***" if cred.access_token else "",
                "redirect_uri": "",  # We'd need to store this separately
                "connected": cred.access_token is not None
            }
    
    return settings


@router.post("/marketplace")
def save_marketplace_settings(
    data: MarketplaceSettingsInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Save marketplace API credentials.
    These are stored encrypted and used for OAuth flow.
    """
    from src.core.encryption import EncryptionService
    from src.crud.crud_marketplace import marketplace as crud_m
    from src.models.marketplace import MarketplaceAppCredential
    
    # Map names to proper marketplace names
    name_map = {
        "amazon": "Amazon",
        "mercadolibre": "MercadoLibre"
    }
    
    marketplace_name = name_map.get(data.marketplace.lower())
    if not marketplace_name:
        raise HTTPException(status_code=400, detail="Unknown marketplace")
    
    # Find or create the marketplace
    m = db.query(crud_m.model).filter(crud_m.model.name == marketplace_name).first()
    if not m:
        from src.schemas.marketplace import MarketplaceCreate
        api_urls = {
            "Amazon": "https://sellingpartnerapi-na.amazon.com",
            "MercadoLibre": "https://api.mercadolibre.com"
        }
        m_in = MarketplaceCreate(name=marketplace_name, api_base_url=api_urls[marketplace_name])
        m = crud_m.create(db, obj_in=m_in)
    
    # Check if app credentials exist for this user/marketplace
    existing = db.query(MarketplaceAppCredential).filter(
        MarketplaceAppCredential.user_id == current_user.id,
        MarketplaceAppCredential.marketplace_id == m.id
    ).first()
    
    encryption = EncryptionService()
    encrypted_secret = encryption.encrypt(data.client_secret)
    
    if existing:
        existing.client_id = data.client_id
        existing.client_secret_encrypted = encrypted_secret
        existing.redirect_uri = data.redirect_uri
        db.commit()
    else:
        new_cred = MarketplaceAppCredential(
            user_id=current_user.id,
            marketplace_id=m.id,
            client_id=data.client_id,
            client_secret_encrypted=encrypted_secret,
            redirect_uri=data.redirect_uri
        )
        db.add(new_cred)
        db.commit()
    
    return {"status": "success", "message": f"{marketplace_name} credentials saved"}


@router.get("/marketplace/{marketplace_name}/test")
async def test_marketplace_connection(
    marketplace_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Test if marketplace credentials are valid.
    """
    # For now, just return success if credentials exist
    from src.crud.crud_marketplace import marketplace as crud_m
    from src.models.marketplace import MarketplaceAppCredential
    
    name_map = {
        "amazon": "Amazon",
        "mercadolibre": "MercadoLibre"
    }
    
    proper_name = name_map.get(marketplace_name.lower())
    if not proper_name:
        return {"success": False, "error": "Unknown marketplace"}
    
    m = db.query(crud_m.model).filter(crud_m.model.name == proper_name).first()
    if not m:
        return {"success": False, "error": "Marketplace not configured"}
    
    cred = db.query(MarketplaceAppCredential).filter(
        MarketplaceAppCredential.user_id == current_user.id,
        MarketplaceAppCredential.marketplace_id == m.id
    ).first()
    
    if not cred:
        return {"success": False, "error": "No credentials found"}
    
    if not cred.client_id:
        return {"success": False, "error": "Client ID not set"}
    
    return {"success": True, "message": "Credentials configured"}
