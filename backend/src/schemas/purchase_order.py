from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime

# Import related schemas for nesting
from .product import Product
from .supplier import Supplier

# --- Schemas for Purchase Order Item ---

class PurchaseOrderItemBase(BaseModel):
    product_id: int
    quantity: int
    cost_per_unit: float

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

# Schema for reading an item, includes nested product details
class PurchaseOrderItem(PurchaseOrderItemBase):
    id: int
    product: Product

    model_config = ConfigDict(from_attributes=True)


# --- Schemas for Purchase Order ---

class PurchaseOrderBase(BaseModel):
    supplier_id: int
    status: str = "PENDING"
    order_date: datetime
    expected_delivery_date: Optional[date] = None

# Schema for creating an order, includes items to be created
class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]

# Schema for updating an order, all fields are optional
class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    status: Optional[str] = None
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[date] = None

# Schema for reading an order, includes nested supplier and item details
class PurchaseOrder(PurchaseOrderBase):
    id: int
    supplier: Supplier
    items: List[PurchaseOrderItem] = []

    model_config = ConfigDict(from_attributes=True)
