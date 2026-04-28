from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
from ..schemas.product import ProductImage

class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    COMPLETED = "completed"
    CLOSED = "closed"

class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"

# --- Purchase Order Item ---
class ProductRef(BaseModel):
    id: int
    name: str
    sku: str
    images: Optional[List[ProductImage]] = [] # Enrich with image data
    variants: Optional[List[Any]] = [] # Included for frontend variant splitting
    
    model_config = ConfigDict(from_attributes=True)

class PurchaseOrderItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity_ordered: float = 0.0
    unit_cost: float = 0.0
    supplier_product_name: Optional[str] = None

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
    product: Optional[ProductRef] = None
    
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

    payment_status: Optional[str] = PaymentStatus.UNPAID.value
    payment_method: Optional[str] = None
    custom_payer_name: Optional[str] = None
    paid_by_user_id: Optional[int] = None
    
    ordered_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    items: Optional[List[PurchaseOrderItemCreate]] = []

class PurchaseOrderUpdate(BaseModel):
    status: Optional[PurchaseOrderStatus] = None
    notes: Optional[str] = None
    shipping_cost: Optional[float] = None
    tax_amount: Optional[float] = None
    other_costs: Optional[float] = None
    exchange_rate: Optional[float] = None
    
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    custom_payer_name: Optional[str] = None
    paid_by_user_id: Optional[int] = None
    
    ordered_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

class PurchaseOrder(PurchaseOrderBase):
    id: int
    total_amount: float
    landed_cost: float
    created_at: datetime
    updated_at: datetime
    ordered_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    items: List[PurchaseOrderItem] = []

    model_config = ConfigDict(from_attributes=True)
