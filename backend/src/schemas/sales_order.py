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
