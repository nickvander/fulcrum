from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from ..schemas.custom_field import ProductCustomField
from ..schemas.inventory import InventoryItem as InventoryItemSchema, InventoryAdjustment as InventoryAdjustmentSchema


# Schema for Product Images
class ProductImageBase(BaseModel):
    image_path: str
    is_primary: Optional[int] = 0
    source: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

class ProductImageCreate(ProductImageBase):
    product_id: int

class ProductImageUpdate(BaseModel):
    is_primary: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None

class ProductImage(ProductImageBase):
    id: int
    product_id: int

    model_config = ConfigDict(from_attributes=True)


# Schema for Products
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    properties: Optional[dict] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None



class Product(ProductBase):
    id: int
    supplier_id: Optional[int] = None
    images: List[ProductImage] = []
    inventory_items: List[InventoryItemSchema] = []
    inventory_adjustments: List[InventoryAdjustmentSchema] = []
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    custom_fields: List[ProductCustomField] = []

    model_config = ConfigDict(from_attributes=True)