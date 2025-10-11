from pydantic import BaseModel, ConfigDict
from typing import Optional

from ..models.custom_field import FieldType

class CustomFieldBase(BaseModel):
    name: str
    type: FieldType

class CustomFieldCreate(CustomFieldBase):
    pass

class CustomFieldUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[FieldType] = None

class CustomField(CustomFieldBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ProductCustomFieldBase(BaseModel):
    custom_field_id: int
    value: str

class ProductCustomFieldCreate(ProductCustomFieldBase):
    product_id: int

class ProductCustomFieldUpdate(BaseModel):
    value: Optional[str] = None

class ProductCustomField(ProductCustomFieldBase):
    id: int
    product_id: int

    model_config = ConfigDict(from_attributes=True)
