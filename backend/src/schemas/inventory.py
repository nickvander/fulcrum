from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StockAdjustment(BaseModel):
    adjustment: int
    reason: Optional[str] = None  # Optional reason for the adjustment

class InventoryItem(BaseModel):
    id: int
    product_id: int
    quantity: int
    location: Optional[str] = None

    class Config:
        from_attributes = True

class InventoryAdjustment(BaseModel):
    id: int
    product_id: int
    adjustment: int  # Positive for increases, negative for decreases
    reason: Optional[str] = None
    timestamp: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True
