from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class PasswordResetTokenCreate(BaseModel):
    email: str  # User's email to send reset link to

class PasswordResetTokenVerify(BaseModel):
    token: str  # The reset token from email
    new_password: str  # The new password to set

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class PasswordResetTokenInDB(BaseModel):
    id: int
    token: str
    user_id: int
    expires_at: str
    used: bool
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