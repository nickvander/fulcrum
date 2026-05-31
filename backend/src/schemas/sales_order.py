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
    # Captured cost basis per unit (NULL on legacy rows). Lets the
    # detail page show per-line margin without re-deriving from the
    # product's current cost.
    cost_per_unit: Optional[float] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrder(BaseModel):
    id: int
    status: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = "MXN"
    created_at: Optional[datetime] = None
    # Plain string (catalog-governed) rather than a fixed enum, so an
    # order from a marketplace newly added to the catalog still
    # serializes instead of failing schema validation.
    source: Optional[str] = None
    external_order_id: Optional[str] = None
    # Net margin % from the order's OrderCostBreakdown (1:1). None means
    # "no margin data" — either the order has no breakdown row, or revenue
    # was zero (dividing by zero would lie). The UI renders None as an
    # em-dash, never 0%.
    net_margin_percent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrderListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/sales-orders/.

    `total` is the count of rows matching the filters+search BEFORE
    skip/limit, so the operator UI can render `Showing N–M of Total` and
    drive a server-side paginator. `skip`/`limit` are echoed back so the
    client never has to assume its own request was honored.
    """
    items: List["SalesOrder"]
    total: int
    skip: int
    limit: int


class OrderCostBreakdownRead(BaseModel):
    """The Phase-8 cost engine's per-order economics. `*_mxn` fields
    are the MXN-normalized equivalents at the order-date FX rate."""
    currency: str
    exchange_rate_to_mxn: float
    revenue_amount: float
    revenue_amount_mxn: float
    cogs_amount: float
    marketplace_fees_amount: float
    shipping_cost_amount: float
    ad_spend_amount: float
    other_cost_amount: float
    total_cost_amount: float
    net_profit_amount: float
    net_margin_percent: Optional[float] = None
    # 'estimated' (from the marketplace's default fee rate) or
    # 'settled' (real numbers from the finance API).
    fees_source: str
    fees_synced_at: Optional[datetime] = None
    reversed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OrderStatusEventRead(BaseModel):
    """One row of the order's status timeline."""
    from_status: Optional[str] = None
    to_status: str
    changed_at: datetime
    source_signal: str

    model_config = ConfigDict(from_attributes=True)


class OrderRefundEventRead(BaseModel):
    """An Amazon partial-refund event recorded against the order."""
    refund_id: str
    posted_at: Optional[datetime] = None
    refund_amount: float
    currency: str


class SalesOrderDetail(SalesOrder):
    items: List[SalesOrderItem] = []
    # Full economics + lifecycle, surfaced so the detail page shows the
    # complete picture the API knows about — not just the total.
    cost_breakdown: Optional[OrderCostBreakdownRead] = None
    status_timeline: List[OrderStatusEventRead] = []
    refund_events: List[OrderRefundEventRead] = []


class SalesOrderChannelBreakdown(BaseModel):
    source: str
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
