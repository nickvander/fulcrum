from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StockAdjustment(BaseModel):
    adjustment: int
    reason: Optional[str] = None  # Optional reason for the adjustment

class InventoryItem(BaseModel):
    id: int
    product_id: Optional[int] = None  # Now optional to support variants-only inventory
    variant_id: Optional[int] = None  # Added for variant support
    quantity: int
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InventoryAdjustment(BaseModel):
    id: int
    product_id: Optional[int] = None  # Now optional to support variants-only adjustments
    variant_id: Optional[int] = None  # Added for variant support
    adjustment: int  # Positive for additions, negative for subtractions
    reason: Optional[str] = None
    created_at: Optional[datetime] = None  # Changed from timestamp to match model, made optional for existing records
    created_by: Optional[str] = None  # Made optional to handle existing records

    class Config:
        from_attributes = True
