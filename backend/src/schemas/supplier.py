from pydantic import BaseModel, EmailStr, ConfigDict

class SupplierBase(BaseModel):
    """Base schema for a supplier."""
    name: str
    contact_person: str | None = None
    email: EmailStr
    phone: str | None = None

class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier."""
    pass

class Supplier(SupplierBase):
    """Schema for reading a supplier, including the database ID."""
    id: int

    model_config = ConfigDict(from_attributes=True)
