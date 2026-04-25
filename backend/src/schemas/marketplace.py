from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class MarketplaceBase(BaseModel):
    name: str
    api_base_url: Optional[str] = None

class MarketplaceCreate(MarketplaceBase):
    pass

class MarketplaceUpdate(MarketplaceBase):
    pass

class Marketplace(MarketplaceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class MarketplaceListingBase(BaseModel):
    product_id: int
    marketplace_id: int
    external_listing_id: Optional[str] = None
    listing_url: Optional[str] = None
    status: Optional[str] = None
    sync_status: Optional[str] = "PENDING"
    last_sync: Optional[datetime] = None
    marketplace_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class MarketplaceListingCreate(MarketplaceListingBase):
    pass

class MarketplaceListingUpdate(BaseModel):
    external_listing_id: Optional[str] = None
    listing_url: Optional[str] = None
    status: Optional[str] = None
    sync_status: Optional[str] = None
    marketplace_price: Optional[float] = None
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class MarketplaceListing(MarketplaceListingBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
