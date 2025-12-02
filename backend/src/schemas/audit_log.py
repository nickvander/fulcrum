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
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)