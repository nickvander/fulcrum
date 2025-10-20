from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AddressBase(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    is_primary: Optional[bool] = False
    is_billing: Optional[bool] = False
    is_shipping: Optional[bool] = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(AddressBase):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_primary: Optional[bool] = None
    is_billing: Optional[bool] = None
    is_shipping: Optional[bool] = None

class Address(AddressBase):
    id: int
    user_id: int
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