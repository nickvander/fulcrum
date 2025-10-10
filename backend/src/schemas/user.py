from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None
    is_superuser: Optional[bool] = None

class User(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None