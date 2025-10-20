from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserAuditLogBase(BaseModel):
    user_id: int  # The user that the action was performed on
    action_performed_by: int  # The user who performed the action
    action: str  # e.g., 'create', 'update', 'delete', 'password_reset'
    details: Optional[str] = None  # Additional details about the action
    ip_address: Optional[str] = None  # IP address of the user who performed the action
    user_agent: Optional[str] = None  # User agent of the user who performed the action


class UserAuditLogCreate(UserAuditLogBase):
    pass


class UserAuditLogUpdate(BaseModel):
    details: Optional[str] = None


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