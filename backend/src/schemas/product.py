from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    properties: Optional[dict] = None

class Product(ProductBase):
    id: int
    supplier_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)