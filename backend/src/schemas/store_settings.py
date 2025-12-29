from pydantic import BaseModel, ConfigDict
from typing import Dict, Any

class StoreSettingsBase(BaseModel):
    settings: Dict[str, Any] = {}
    low_inventory_days_default: int = 30
    low_stock_quantity_default: int = 10

class StoreSettingsCreate(StoreSettingsBase):
    pass

class StoreSettingsUpdate(StoreSettingsBase):
    pass

class StoreSettings(StoreSettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
