from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductInventorySettingsBase(BaseModel):
    product_id: int
    low_inventory_days_threshold: Optional[int] = None
    low_stock_quantity_threshold: Optional[int] = None

class ProductInventorySettingsCreate(ProductInventorySettingsBase):
    pass

class ProductInventorySettingsUpdate(BaseModel):
    low_inventory_days_threshold: Optional[int] = None
    low_stock_quantity_threshold: Optional[int] = None

class ProductInventorySettings(ProductInventorySettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
