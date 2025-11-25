from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserAuditLogBase(BaseModel):
    user_id: int
    action_performed_by: int
    action: str
    details: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserAuditLogCreate(UserAuditLogBase):
    pass

class UserAuditLogUpdate(UserAuditLogBase):
    pass

class UserAuditLog(UserAuditLogBase):
    id: int
    created_at: Optional[str] = None
    
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