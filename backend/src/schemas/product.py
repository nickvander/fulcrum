from pydantic import BaseModel, ConfigDict

class ProductBase(BaseModel):
    """Base schema for a product, containing common attributes."""
    name: str
    description: str | None = None
    sku: str
    default_resale_price: float
    cost_price: float

class ProductCreate(ProductBase):
    """Schema used for creating a new product. Inherits from ProductBase."""
    pass

class Product(ProductBase):
    """
    Schema for reading a product, including the database ID.
    """
    id: int
    supplier_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
