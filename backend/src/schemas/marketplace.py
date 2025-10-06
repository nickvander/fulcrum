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
