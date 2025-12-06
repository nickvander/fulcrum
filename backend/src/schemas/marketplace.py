from pydantic import BaseModel, ConfigDict
from typing import Optional

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

class MarketplaceListing(MarketplaceListingBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
