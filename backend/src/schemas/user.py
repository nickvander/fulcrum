from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime

class UserType(str, Enum):
    admin = "admin"
    employee = "employee" 
    customer = "customer"

class UserBase(BaseModel):
    email: EmailStr
    is_superuser: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_type: Optional[UserType] = None
    is_active: bool = True
    avatar: Optional[str] = None
    force_password_change: bool = False

class UserCreate(UserBase):
    password: str
    employee_id: Optional[str] = None  # Optional: if not provided, system will auto-generate
    force_password_change: Optional[bool] = None # Allow setting this on creation
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_superuser: Optional[bool] = None
    employee_id: Optional[str] = None
    force_password_change: Optional[bool] = None

class User(UserBase):
    id: int
    employee_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    force_password_change: bool = False
    
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
        
        # Ensure force_password_change is False if None (e.g. from legacy data)
        if data.get('force_password_change') is None:
            data['force_password_change'] = False
            
        return cls(**data)
    
    model_config = ConfigDict(from_attributes=True)

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None

class UserEmail(BaseModel):
    email: EmailStr

class UserListParams(BaseModel):
    skip: int = 0
    limit: int = 100
    user_type: Optional[UserType] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None