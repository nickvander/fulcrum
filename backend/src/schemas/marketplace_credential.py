from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class MarketplaceCredentialBase(BaseModel):
    marketplace_id: int
    token_type: Optional[str] = None
    scopes: Optional[str] = None
    expires_at: Optional[datetime] = None

class MarketplaceCredentialCreate(MarketplaceCredentialBase):
    """
    Schema for creating a new credential.
    Tokens are provided in plaintext here and will be encrypted by the CRUD/Service layer.
    """
    access_token: str
    refresh_token: str

class MarketplaceCredentialUpdate(BaseModel):
    """
    Schema for updating existing credentials.
    """
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    scopes: Optional[str] = None
    expires_at: Optional[datetime] = None

class MarketplaceCredential(MarketplaceCredentialBase):
    """
    Schema for returning credential metadata.
    SENSITIVE TOKENS ARE EXCLUDED.
    """
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class MarketplaceCredentialInternal(MarketplaceCredential):
    """
    Schema for internal use where decrypted tokens are needed.
    NEVER return this in an API response.
    """
    access_token: str
    refresh_token: str
