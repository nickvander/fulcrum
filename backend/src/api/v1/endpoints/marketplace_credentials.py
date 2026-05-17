from typing import List, Any
from fastapi import APIRouter, Depends
from src.core.errors import LocalizedHTTPException
from sqlalchemy.orm import Session

from src.api import dependencies
from src.database import get_db
from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
from src.schemas.marketplace_credential import (
    MarketplaceCredential,
    MarketplaceCredentialCreate,
    MarketplaceCredentialUpdate
)
from src.models.user import User

router = APIRouter()

@router.post("/", response_model=MarketplaceCredential)
def create_credential(
    *,
    db: Session = Depends(get_db),
    credential_in: MarketplaceCredentialCreate,
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Create or update marketplace credentials for the current user.
    """
    # Check if credential already exists for this marketplace
    existing = crud_cred.get_by_marketplace(
        db, user_id=current_user.id, marketplace_id=credential_in.marketplace_id
    )
    if existing:
        # Update instead of create
        update_data = MarketplaceCredentialUpdate(**credential_in.model_dump())
        return crud_cred.update_with_encryption(db, db_obj=existing, obj_in=update_data)
    
    return crud_cred.create_with_owner(db, obj_in=credential_in, user_id=current_user.id)

@router.get("/", response_model=List[MarketplaceCredential])
def read_credentials(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Retrieve all marketplace credentials for the current user.
    """
    return crud_cred.get_multi_by_owner(db, user_id=current_user.id, skip=skip, limit=limit)

@router.get("/{marketplace_id}", response_model=MarketplaceCredential)
def read_credential_by_marketplace(
    marketplace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Get credential metadata for a specific marketplace.
    """
    credential = crud_cred.get_by_marketplace(db, user_id=current_user.id, marketplace_id=marketplace_id)
    if not credential:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.notFoundForMarketplace",
            params={"marketplaceId": marketplace_id},
            detail="Credentials not found for this marketplace",
        )
    return credential

@router.delete("/{id}", response_model=MarketplaceCredential)
def delete_credential(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Delete/revoke marketplace credentials.
    """
    credential = crud_cred.get(db, id=id)
    if not credential:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.notFound",
            params={"id": id},
            detail="Credential not found",
        )
    if credential.user_id != current_user.id and not current_user.is_superuser:
        raise LocalizedHTTPException(
            status_code=403,
            code="apiErrors.user.notEnoughPrivileges",
            detail="Not enough permissions",
        )
    
    return crud_cred.remove(db, id=id)

@router.get("/by-name/{marketplace_name}/authorize")
async def authorize_marketplace_by_name(
    marketplace_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Get the authorization URL for a marketplace by name.
    Creates the marketplace entry if it doesn't exist.
    """
    from src.crud.crud_marketplace import marketplace as crud_m
    from src.schemas.marketplace import MarketplaceCreate
    
    # Map names to API URLs
    marketplace_configs = {
        "amazon": {"name": "Amazon", "api_base_url": "https://sellingpartnerapi-na.amazon.com"},
        "mercadolibre": {"name": "MercadoLibre", "api_base_url": "https://api.mercadolibre.com"},
    }
    
    name_lower = marketplace_name.lower()
    if name_lower not in marketplace_configs:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.marketplaceCredentials.unsupportedMarketplace",
            params={"name": marketplace_name},
            detail=f"Unsupported marketplace: {marketplace_name}",
        )
    
    config = marketplace_configs[name_lower]
    
    # Find or create the marketplace
    m = db.query(crud_m.model).filter(crud_m.model.name == config["name"]).first()
    if not m:
        m_in = MarketplaceCreate(name=config["name"], api_base_url=config["api_base_url"])
        m = crud_m.create(db, obj_in=m_in)
    
    from src.services.marketplace_service import marketplace_service
    connector = marketplace_service.get_connector(m.name)
    auth_url = await connector.get_auth_url()
    
    return {"auth_url": auth_url, "marketplace_id": m.id}

@router.get("/{marketplace_id}/authorize")
async def authorize_marketplace(
    marketplace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Get the authorization URL for a specific marketplace by ID.
    """
    from src.crud.crud_marketplace import marketplace as crud_m
    m = crud_m.get(db, id=marketplace_id)
    if not m:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.marketplaceNotFound",
            params={"id": marketplace_id},
            detail="Marketplace not found",
        )
    
    from src.services.marketplace_service import marketplace_service
    connector = marketplace_service.get_connector(m.name)
    auth_url = await connector.get_auth_url()
    return {"auth_url": auth_url}

@router.get("/{marketplace_id}/callback")
async def callback_marketplace(
    marketplace_id: int,
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Handle OAuth callback and store credentials.
    """
    from src.crud.crud_marketplace import marketplace as crud_m
    m = crud_m.get(db, id=marketplace_id)
    if not m:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.marketplaceNotFound",
            params={"id": marketplace_id},
            detail="Marketplace not found",
        )
    
    from src.services.marketplace_service import marketplace_service
    connector = marketplace_service.get_connector(m.name)
    
    try:
        token_data = await connector.exchange_code_for_token(code)
    except Exception as e:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.marketplaceCredentials.tokenExchangeFailed",
            params={"reason": str(e)},
            detail=f"Failed to exchange code: {str(e)}",
        )
    
    from datetime import datetime, timedelta
    expires_at = None
    if "expires_in" in token_data:
        expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
    
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=marketplace_id,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_type=token_data.get("token_type", "Bearer"),
        scopes=token_data.get("scope"),
        expires_at=expires_at
    )
    
    # Use existing create_credential logic (which handles updates)
    existing = crud_cred.get_by_marketplace(
        db, user_id=current_user.id, marketplace_id=marketplace_id
    )
    if existing:
        update_data = MarketplaceCredentialUpdate(**cred_in.model_dump())
        crud_cred.update_with_encryption(db, db_obj=existing, obj_in=update_data)
    else:
        crud_cred.create_with_owner(db, obj_in=cred_in, user_id=current_user.id)
    
    return {"status": "success", "message": "Credentials stored successfully"}
