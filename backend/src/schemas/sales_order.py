from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OrderSourceSchema(str, Enum):
    FULCRUM = "FULCRUM"
    MERCADOLIBRE = "MERCADOLIBRE"
    AMAZON = "AMAZON"


class SalesOrderItem(BaseModel):
    id: int
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    price_per_unit: Optional[float] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrder(BaseModel):
    id: int
    status: Optional[str] = None
    total_price: Optional[float] = None
    created_at: Optional[datetime] = None
    source: Optional[OrderSourceSchema] = None
    external_order_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrderDetail(SalesOrder):
    items: List[SalesOrderItem] = []


class SalesOrderChannelBreakdown(BaseModel):
    source: OrderSourceSchema
    count: int
    revenue: float


class SalesOrderSummary(BaseModel):
    window_days: int
    total_orders: int
    total_revenue: float
    open_orders: int
    by_channel: List[SalesOrderChannelBreakdown]


# --- Returns ---------------------------------------------------------------


class SalesOrderReturnLineInput(BaseModel):
    """One return line from the operator. At least one of
    `order_item_id` or `product_id` is required; the service falls
    back to the item's product_id when only `order_item_id` is set."""
    order_item_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: int


class SalesOrderReturnCreate(BaseModel):
    """Payload for `POST /sales-orders/{order_id}/returns`. One call
    can record multiple lines — multi-line orders often come back in
    pieces (e.g. buyer returned 2 of 3 SKUs)."""
    lines: List[SalesOrderReturnLineInput]
    reason: Optional[str] = None
    notes: Optional[str] = None


class SalesOrderReturnRead(BaseModel):
    """One persisted return row. Read-only — operators can't edit a
    recorded return; mistakes are corrected with a manual stock
    adjustment + a new return row with notes explaining the fix."""
    id: int
    order_id: int
    order_item_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    received_at: datetime
    recorded_by_user_id: Optional[int] = None
    recorded_by_email: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
