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

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    supplier_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)