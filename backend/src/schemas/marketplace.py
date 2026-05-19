from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class MarketplaceBase(BaseModel):
    name: str
    api_base_url: Optional[str] = None
    # Phase-8 cost-engine config. Both default to 0 so a newly-
    # connected marketplace returns the same gross-margin number the
    # old reports always showed until the operator configures real
    # rates. See `services/order_cost_engine.py`.
    default_fee_rate: float = 0.0
    default_shipping_cost: float = 0.0

class MarketplaceCreate(MarketplaceBase):
    pass

class MarketplaceUpdate(MarketplaceBase):
    pass


class MarketplaceFeeConfigUpdate(BaseModel):
    """PATCH body for the fee-config form on the marketplace detail
    page. Both fields are optional so the form can update one
    without clobbering the other.
    """
    default_fee_rate: Optional[float] = None
    default_shipping_cost: Optional[float] = None


class MarketplaceFeeConfigRecomputeResult(BaseModel):
    """Returned by `POST /marketplaces/{id}/recompute-cost-breakdowns`.
    Mirrors the shape the cost engine's `recompute_for_orders` emits
    so the UI can render "X breakdowns updated, Y created, Z errors"
    after the operator clicks recompute."""
    breakdowns_created: int
    breakdowns_updated: int
    errors: int


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
    available_quantity: Optional[int] = None
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
