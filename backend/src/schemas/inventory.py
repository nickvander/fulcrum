from pydantic import BaseModel, ConfigDict
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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_orm(cls, obj):
        # Convert datetime objects to strings for JSON serialization
        data = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if value is not None and isinstance(value, datetime):
                data[field_name] = value.isoformat()
            else:
                data[field_name] = value
        return cls(**data)
    
    model_config = ConfigDict(from_attributes=True)

class InventoryAdjustment(BaseModel):
    id: int
    product_id: Optional[int] = None  # Now optional to support variants-only adjustments
    variant_id: Optional[int] = None  # Added for variant support
    adjustment: int  # Positive for additions, negative for subtractions
    reason: Optional[str] = None
    created_at: Optional[str] = None  # Changed from timestamp to match model, made optional for existing records
    created_by: Optional[str] = None  # Made optional to handle existing records
    
    @classmethod
    def from_orm(cls, obj):
        # Convert datetime objects to strings for JSON serialization
        data = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if value is not None and isinstance(value, datetime):
                data[field_name] = value.isoformat()
            else:
                data[field_name] = value
        return cls(**data)
    
    model_config = ConfigDict(from_attributes=True)
