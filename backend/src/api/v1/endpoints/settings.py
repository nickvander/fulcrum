"""
Settings API endpoints for managing marketplace credentials and other configuration.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.api import dependencies
from src.api.dependencies import get_db
from src.core.errors import LocalizedHTTPException
from src.models.user import User
from src.schemas.store_settings import SMTPConfigCreate

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
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.setting.unknownMarketplace",
            params={"marketplace": data.marketplace},
            detail="Unknown marketplace",
        )
    
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


# =============================================================================
# SMTP / Email Settings (Store-Level)
# =============================================================================

@router.get("/smtp")
def get_smtp_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Get store-level SMTP email settings.
    Password is never returned.
    """
    from src.crud.crud_store_settings import store_settings as crud_ss
    
    settings = crud_ss.get_settings(db)
    smtp_config = settings.settings.get("smtp", {})
    
    return {
        "provider": smtp_config.get("provider", "custom"),
        "host": smtp_config.get("host", ""),
        "port": smtp_config.get("port", 587),
        "username": smtp_config.get("username", ""),
        "from_email": smtp_config.get("from_email", ""),
        "from_name": smtp_config.get("from_name", ""),
        "use_tls": smtp_config.get("use_tls", True),
        "use_ssl": smtp_config.get("use_ssl", False),
        "is_configured": bool(smtp_config.get("username") and settings.smtp_password_encrypted),
    }


@router.post("/smtp")
def save_smtp_settings(
    data: SMTPConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Save store-level SMTP settings.
    Password is encrypted before storage.
    """
    from src.crud.crud_store_settings import store_settings as crud_ss
    from src.core.encryption import encryption_service
    from src.services.marketing.smtp import EMAIL_PROVIDER_PRESETS
    
    settings = crud_ss.get_settings(db)
    
    # Get preset config if provider specified
    preset = EMAIL_PROVIDER_PRESETS.get(data.provider, {})
    
    # Build SMTP config
    smtp_config = {
        "provider": data.provider,
        "host": data.host or preset.get("host", ""),
        "port": data.port or preset.get("port", 587),
        "username": data.username,
        "from_email": data.from_email or data.username,
        "from_name": data.from_name or "",
        "use_tls": data.use_tls if data.host else preset.get("use_tls", True),
        "use_ssl": data.use_ssl if data.host else preset.get("use_ssl", False),
    }
    
    # Update settings JSON
    current_settings = settings.settings or {}
    current_settings["smtp"] = smtp_config
    settings.settings = current_settings
    
    # Encrypt and store password if provided
    if data.password:
        settings.smtp_password_encrypted = encryption_service.encrypt(data.password)
    
    db.commit()
    db.refresh(settings)
    
    return {"status": "success", "message": "SMTP settings saved"}


@router.post("/smtp/test")
async def test_smtp_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Dict[str, Any]:
    """
    Test SMTP connection with saved credentials.
    """
    from src.crud.crud_store_settings import store_settings as crud_ss
    from src.core.encryption import encryption_service
    
    settings = crud_ss.get_settings(db)
    smtp_config = settings.settings.get("smtp", {})
    
    if not smtp_config.get("username") or not settings.smtp_password_encrypted:
        return {"success": False, "error": "SMTP not configured"}
    
    try:
        # Build config for connector
        config = {
            **smtp_config,
            "password": encryption_service.decrypt(settings.smtp_password_encrypted),
        }
        
        # Try to validate (import here to avoid circular imports)
        from src.services.marketing import get_connector, CONNECTOR_REGISTRY
        
        if "smtp" not in CONNECTOR_REGISTRY:
            return {"success": False, "error": "SMTP connector not available (install aiosmtplib)"}
        
        connector = get_connector("smtp", config)
        is_valid = await connector.validate_credentials()
        
        if is_valid:
            return {"success": True, "message": "SMTP connection successful"}
        else:
            return {"success": False, "error": "Failed to connect to SMTP server"}
    except Exception as e:
        return {"success": False, "error": str(e)}

