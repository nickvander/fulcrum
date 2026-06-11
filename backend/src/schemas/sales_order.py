from pydantic import BaseModel, ConfigDict, Field
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


# --- On-site order create (FP-04) ------------------------------------------


class SalesOrderItemCreate(BaseModel):
    """One requested line on an on-site order.

    Carries NO price — the server prices each line authoritatively from
    the product (or the variant, when `variant_id` is set) so a client
    can never dictate what it pays. `quantity` must be a positive int.
    """

    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)


class SalesOrderCreate(BaseModel):
    """Payload for `POST /sales-orders/`.

    `idempotency_key` is required and stored as the order's
    `external_order_id` (with `source=FULCRUM`); a retry with the same
    key returns the already-created order instead of decrementing stock
    a second time. `items` must be non-empty. Prices are NEVER part of
    the request — the server is the pricing authority.
    """

    idempotency_key: str = Field(..., min_length=1)
    items: List[SalesOrderItemCreate] = Field(..., min_length=1)
    currency: str = "MXN"
    location: str = "default"
    # The storefront customer (User id) placing the order, resolved by the BFF
    # from the customer's session JWT (NEVER client-supplied at the storefront).
    # Stored on the order as the ownership anchor for customer self-service
    # (returns Phase 2). NULL for operator/marketplace orders.
    customer_user_id: Optional[int] = Field(default=None, gt=0)
    # Optional stock-reservation key (OXXO/SPEI). When set and an ACTIVE
    # reservation exists for it, the order CONSUMES the hold instead of
    # decrementing stock again (the stock already left on-hand at reserve time).
    # If the reservation is missing/expired the order falls back to a normal
    # atomic decrement (which 409s on insufficient stock, as today).
    reservation_key: Optional[str] = Field(default=None, min_length=1)

    # Optional storefront discount code (FP discount codes). Validated + applied
    # ATOMICALLY at order-create: the server recomputes the amount on its own
    # subtotal (never a client value), serializes on the code row, and fails the
    # order if the code is invalid/expired/limit-reached. NULL ⇒ no discount.
    discount_code: Optional[str] = Field(default=None, min_length=1, max_length=64)

    # CFDI 4.0 receptor (buyer fiscal data), captured at checkout when the buyer
    # requests a factura (FP-06 P2). All optional: a NULL RFC ⇒ público en general
    # (RFC genérico) per cfdi_service. Lengths mirror the SalesOrder columns so a
    # malformed value is rejected here rather than at the DB. When an RFC is
    # present the order-create endpoint stamps an ingreso CFDI (best-effort).
    cfdi_receiver_rfc: Optional[str] = Field(default=None, max_length=13)
    cfdi_receiver_name: Optional[str] = Field(default=None, max_length=255)
    cfdi_receiver_postal_code: Optional[str] = Field(default=None, max_length=5)
    cfdi_receiver_regime: Optional[str] = Field(default=None, max_length=8)
    cfdi_use: Optional[str] = Field(default=None, max_length=8)


class SalesOrderShippingChargeUpdate(BaseModel):
    """Persist the shipping charge selected by the storefront BFF.

    Vendio sends money in centavos. Fulcrum stores monetary values as
    Float, so the API endpoint converts `amount_cents` at the boundary.
    """

    idempotency_key: str = Field(..., min_length=1)
    rate_id: Optional[str] = None
    provider: str = Field(..., min_length=1)
    carrier: str = Field(..., min_length=1)
    service: str = Field(..., min_length=1)
    amount_cents: int = Field(..., ge=0)
    currency: str = "MXN"
    estimated_days: Optional[int] = Field(default=None, ge=0)


class SalesOrderShippingLabelUpdate(BaseModel):
    """Persist a purchased shipping label against the Fulcrum order."""

    idempotency_key: str = Field(..., min_length=1)
    shipment_id: Optional[str] = None
    provider: str = Field(..., min_length=1)
    carrier: str = Field(..., min_length=1)
    tracking_number: Optional[str] = None
    label_url: Optional[str] = None
    tracking_url: Optional[str] = None


class SalesOrderFulfillmentRead(BaseModel):
    order_id: int
    shipping_rate_id: Optional[str] = None
    shipping_provider: Optional[str] = None
    shipping_carrier: Optional[str] = None
    shipping_service: Optional[str] = None
    shipping_cost: Optional[float] = None
    shipping_currency: Optional[str] = None
    shipping_estimated_days: Optional[int] = None
    shipping_charge_idempotency_key: Optional[str] = None
    shipping_shipment_id: Optional[str] = None
    shipping_tracking_number: Optional[str] = None
    shipping_label_url: Optional[str] = None
    shipping_tracking_url: Optional[str] = None
    shipping_label_idempotency_key: Optional[str] = None


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
    # Returns Phase 2 lifecycle fields (None/legacy-safe on old rows).
    status: Optional[str] = None
    requested_by_user_id: Optional[int] = None
    amount: Optional[float] = None
    refund_reference: Optional[str] = None
    refunded_at: Optional[datetime] = None
    # Whether these units re-credit sellable inventory on approval (False for
    # defective/damaged — written off, not restocked).
    restock: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# --- Customer self-service returns (Phase 2) -------------------------------- #


class CustomerReturnCreate(BaseModel):
    """Payload for `POST /customers/me/orders/{order_id}/returns`.

    A customer requests a return on their OWN order (ownership is enforced by
    the endpoint). The refund amount is NEVER trusted from the client — Fulcrum
    derives it server-side from the order's line prices. `idempotency_key`
    dedups a double-submit into a single request.
    """

    lines: List[SalesOrderReturnLineInput]
    reason: Optional[str] = None
    idempotency_key: str = Field(..., min_length=1, max_length=128)


class CustomerReturnTransition(BaseModel):
    """Operator-driven status transition for a return (write-scoped, used by the
    BFF approval path). `refund_reference` is stamped when moving to refunded."""

    status: str = Field(..., min_length=1, max_length=20)
    refund_reference: Optional[str] = Field(default=None, max_length=255)


class CustomerOrderItem(BaseModel):
    """A customer-facing order line. Deliberately carries NO cost/margin
    field (`cost_per_unit` is never serialized to a customer)."""

    id: int
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    price_per_unit: Optional[float] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None


class CustomerReturnRead(BaseModel):
    """A return as shown to the owning customer — status + amount, no operator
    identity or internal notes."""

    id: int
    order_id: int
    order_item_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    status: str
    reason: Optional[str] = None
    amount: Optional[float] = None
    requested_at: datetime
    refunded_at: Optional[datetime] = None
    # Whether these units restock on approval (False = defective/damaged write-off).
    restock: Optional[bool] = None


class CustomerOrderDetail(BaseModel):
    """A customer-facing order detail: the order, its lines, and its returns —
    with cost/margin/supplier fields stripped. Built explicitly by the endpoint
    via an allowlist (defence in depth; the BFF strips again)."""

    id: int
    status: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = "MXN"
    created_at: Optional[datetime] = None
    items: List[CustomerOrderItem] = []
    returns: List[CustomerReturnRead] = []
    # Return eligibility (Phase 2), computed authoritatively server-side so the
    # storefront can show/hide the request form without re-deriving policy.
    returnable: bool = False
    return_window_days: int = 0
    # Why a return can't be requested, when `returnable` is False:
    # "window_expired" | "order_closed" | "fully_returned" | None.
    return_block_reason: Optional[str] = None


class SalesOrderCancelResult(BaseModel):
    """Result of POST /sales-orders/{id}/cancel.

    Minimal by design (no cost breakdown): the caller is the storefront BFF's
    compensation path, which only needs to know the order is cancelled and
    whether stock was re-credited. `stock_recredited` reflects whether the
    order carries a `stock_recredited_at` stamp (set once, on a cancel-before-
    ship transition from a realized status)."""

    id: int
    status: str
    stock_recredited: bool

    model_config = ConfigDict(from_attributes=True)
