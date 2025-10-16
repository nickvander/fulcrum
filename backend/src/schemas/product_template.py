from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# Schema for Custom Field Template
class CustomFieldTemplateBase(BaseModel):
    name: str
    type: Optional[str] = "text"  # text, number, boolean, etc.
    default_value: Optional[str] = None
    required: Optional[bool] = False


class CustomFieldTemplateCreate(CustomFieldTemplateBase):
    template_id: int


class CustomFieldTemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    default_value: Optional[str] = None
    required: Optional[bool] = None


class CustomFieldTemplate(CustomFieldTemplateBase):
    id: int
    template_id: int

    model_config = ConfigDict(from_attributes=True)


# Schema for Product Templates
class ProductTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    manufacturer: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    properties: Optional[str] = None  # JSON string for additional properties


class ProductTemplateCreate(ProductTemplateBase):
    pass


class ProductTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    manufacturer: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    properties: Optional[str] = None


class ProductTemplate(ProductTemplateBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: List[CustomFieldTemplate] = []

    model_config = ConfigDict(from_attributes=True)