from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    COMPLETED = "completed"
    CLOSED = "closed"

# --- Purchase Order Item ---
class PurchaseOrderItemBase(BaseModel):
    product_id: int
    quantity_ordered: float = 0.0
    unit_cost: float = 0.0

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItemUpdate(BaseModel):
    quantity_ordered: Optional[float] = None
    quantity_received: Optional[float] = None
    unit_cost: Optional[float] = None

class PurchaseOrderItem(PurchaseOrderItemBase):
    id: int
    po_id: int
    quantity_received: float = 0.0
    
    # Cost breakdown fields
    base_cost: float = 0.0
    shipping_allocated: float = 0.0
    taxes_allocated: float = 0.0
    other_allocated: float = 0.0
    costs_applied_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- Purchase Order ---
class PurchaseOrderBase(BaseModel):
    supplier_id: int
    status: Optional[PurchaseOrderStatus] = PurchaseOrderStatus.DRAFT
    currency: Optional[str] = "USD"
    exchange_rate: Optional[float] = 1.0
    notes: Optional[str] = None
    
    shipping_cost: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    other_costs: Optional[float] = 0.0

class PurchaseOrderCreate(PurchaseOrderBase):
    items: Optional[List[PurchaseOrderItemCreate]] = []

class PurchaseOrderUpdate(BaseModel):
    status: Optional[PurchaseOrderStatus] = None
    notes: Optional[str] = None
    shipping_cost: Optional[float] = None
    tax_amount: Optional[float] = None
    other_costs: Optional[float] = None
    exchange_rate: Optional[float] = None

class PurchaseOrder(PurchaseOrderBase):
    id: int
    total_amount: float
    landed_cost: float
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseOrderItem] = []

    model_config = ConfigDict(from_attributes=True)
