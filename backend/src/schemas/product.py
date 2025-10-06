"""
Pydantic schemas for the Product model.

These schemas define the data structures for creating, reading, and updating
products through the API. They provide data validation and serialization.
"""
from pydantic import BaseModel

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

    This model is used as the response model for API endpoints that return
    product data.
    """
    id: int
    supplier_id: int | None = None

    class Config:
        """Pydantic configuration to enable ORM mode."""
        orm_mode = True
