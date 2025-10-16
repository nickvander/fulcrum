from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# Schema for Product Variants
class ProductVariantBase(BaseModel):
    product_id: int
    name: str
    sku: str
    description: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    attributes: Optional[str] = None  # JSON string containing variant attributes


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    attributes: Optional[str] = None


class ProductVariant(ProductVariantBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Schema for Inventory Items (updated to include variant_id)
class InventoryItemBase(BaseModel):
    product_id: Optional[int] = None  # Make optional to support variants-only inventory
    variant_id: Optional[int] = None  # Make optional to support product-only inventory
    quantity: int
    location: Optional[str] = "default"


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    quantity: Optional[int] = None
    location: Optional[str] = None


class InventoryItem(InventoryItemBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Schema for Inventory Adjustments (updated to include variant_id)
class InventoryAdjustmentBase(BaseModel):
    product_id: Optional[int] = None  # Make optional to support variants
    variant_id: Optional[int] = None  # Make optional to support base products
    adjustment: int  # Positive for additions, negative for subtractions
    reason: Optional[str] = None
    created_by: str


class InventoryAdjustmentCreate(InventoryAdjustmentBase):
    pass


class InventoryAdjustment(InventoryAdjustmentBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)