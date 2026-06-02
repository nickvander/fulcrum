from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


class OrderSource(str, enum.Enum):
    """Named constants for the core order sources.

    This is intentionally NOT the exhaustive list — `SalesOrder.source`
    is a plain string column whose valid values come from the
    marketplace catalog (`marketplace_catalog.order_sources()`). These
    members are convenience constants for the channels referenced by
    name in code; a marketplace added to the catalog is a valid source
    without being added here.

    Subclassing `str` means each member IS its string value, so
    `OrderSource.AMAZON == "AMAZON"` is True and the members are
    interchangeable with the raw strings the DB column stores — in
    comparisons, dict keys, and SQL binds alike.
    """

    FULCRUM = "FULCRUM"
    MERCADOLIBRE = "MERCADOLIBRE"
    AMAZON = "AMAZON"


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    # client_id = Column(Integer, ForeignKey("clients.id")) # Assuming a clients table
    status = Column(String)
    total_price = Column(Float)
    # ISO 4217 code of the marketplace's reported total. Defaults to
    # 'MXN' for back-compat — Mexico is the primary market and every
    # pre-Phase-8 order is implicitly MXN. The Phase-8 cost engine
    # uses this when computing the normalized MXN amount for cross-
    # channel aggregations.
    currency = Column(String(8), nullable=False, default="MXN", server_default="MXN")
    created_at = Column(TIMESTAMP)
    # Plain string (not a DB enum) so adding a marketplace to the catalog
    # doesn't require an `ALTER TYPE ... ADD VALUE` migration. Valid
    # values are governed by `marketplace_catalog.order_sources()`.
    source = Column(String, index=True)
    external_order_id = Column(String)
    shipping_rate_id = Column(String(128), nullable=True)
    shipping_provider = Column(String(64), nullable=True)
    shipping_carrier = Column(String(128), nullable=True)
    shipping_service = Column(String(128), nullable=True)
    shipping_cost = Column(Float, nullable=True)
    shipping_currency = Column(String(8), nullable=True)
    shipping_estimated_days = Column(Integer, nullable=True)
    shipping_charge_idempotency_key = Column(String(128), nullable=True)
    shipping_shipment_id = Column(String(128), nullable=True)
    shipping_tracking_number = Column(String(128), nullable=True)
    shipping_label_url = Column(String, nullable=True)
    shipping_tracking_url = Column(String, nullable=True)
    shipping_label_idempotency_key = Column(String(128), nullable=True)
    # Set by `services/order_lifecycle.py` when an order's stock is
    # credited back to inventory after a cancel-before-ship transition.
    # Non-NULL means "already re-credited, skip on subsequent polls" —
    # the lifecycle service uses this to stay idempotent even when the
    # cancellation webhook fires twice or a poll re-observes the
    # cancelled state.
    stock_recredited_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship("SalesOrderItem", back_populates="order")
    cost_breakdown = relationship(
        "OrderCostBreakdown",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )
    status_events = relationship(
        "SalesOrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="SalesOrderStatusEvent.changed_at",
    )


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_per_unit = Column(Float)
    # Cost basis captured at order-create time so the margin report
    # doesn't drift when Product.cost_price is later updated. NULL on
    # rows ingested before this column existed — the margin SQL falls
    # back to Product.cost_price via COALESCE for those.
    cost_per_unit = Column(Float, nullable=True)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")


class OrderCostBreakdown(Base):
    """Per-order analytics row built by the Phase-8 cost engine.

    1:1 with `SalesOrder`. Carries the components of net margin so
    the dashboard / reports can answer "what did this order actually
    earn after fees + shipping + ad spend?" instead of just gross
    margin (revenue - COGS). Rebuilt by
    `services/order_cost_engine.upsert_breakdown(...)` whenever the
    underlying order is created or updated; also recomputed by a
    Celery beat backfill that catches stale rows.

    Currency:
      - `currency` is the order's own currency (matches
        `SalesOrder.currency`), so rolling up by source preserves
        the marketplace's native numbers.
      - `revenue_amount_mxn` is the same revenue normalized to MXN
        via `exchange_rate_to_mxn`, so cross-channel aggregations
        roll up in one base currency. v1 stores 1.0 — every order
        is MXN today — but the field is wired for future Amazon US
        / international ML expansion.
    """

    __tablename__ = "order_cost_breakdowns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    currency = Column(String(8), nullable=False, default="MXN")
    exchange_rate_to_mxn = Column(Float, nullable=False, default=1.0)

    revenue_amount = Column(Float, nullable=False, default=0.0)
    revenue_amount_mxn = Column(Float, nullable=False, default=0.0)
    cogs_amount = Column(Float, nullable=False, default=0.0)
    marketplace_fees_amount = Column(Float, nullable=False, default=0.0)
    shipping_cost_amount = Column(Float, nullable=False, default=0.0)
    ad_spend_amount = Column(Float, nullable=False, default=0.0)
    other_cost_amount = Column(Float, nullable=False, default=0.0)
    total_cost_amount = Column(Float, nullable=False, default=0.0)
    net_profit_amount = Column(Float, nullable=False, default=0.0)
    # NULL when revenue is 0 — dividing by zero would lie. Caller
    # treats NULL as "no margin data" rather than 0%.
    net_margin_percent = Column(Float, nullable=True)

    # 'estimated' when fees come from Marketplace.default_fee_rate;
    # 'settled' when the settlement-fee ingestion has overwritten
    # marketplace_fees_amount + shipping_cost_amount with real numbers
    # from the marketplace's finance API. The cost engine guards
    # against overwriting 'settled' values with estimates on a
    # subsequent recompute (a stale operator-changed fee rate must not
    # silently revert real settled data).
    fees_source = Column(
        String(16),
        nullable=False,
        default="estimated",
        server_default="estimated",
        index=True,
    )
    fees_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Set when the parent order leaves the realized-status set
    # (cancellation, refund, etc.). The rollup / by-channel / daily
    # aggregators filter on `reversed_at IS NULL` so a reversed order
    # disappears from current-period totals without losing the row
    # itself — the refunds dashboard widget still needs to query it.
    # Cleared if the order ever transitions back into a realized
    # status (rare; e.g. operator-initiated un-cancel).
    reversed_at = Column(DateTime(timezone=True), nullable=True, index=True)

    computed_at = Column(DateTime(timezone=True), nullable=False)

    order = relationship("SalesOrder", back_populates="cost_breakdown")


class AmazonOrderRefund(Base):
    """Persisted SP-API Finances refund event for an Amazon order.

    The settlement-fee worker parses Amazon's `RefundEventList` to net
    fees against the cost-engine breakdown; this table additionally
    persists the refund amount itself so the refunds dashboard can
    surface partial-refund cases where the order's top-level
    `OrderStatus` stays `Shipped` (e.g. the buyer returned one line
    item out of three).

    The `(order_id, amazon_refund_id)` unique constraint provides
    idempotency — the settlement worker re-polls the same financial-
    events payload every hour and must not double-count.
    """

    __tablename__ = "amazon_order_refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amazon_refund_id = Column(String(128), nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    refund_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(8), nullable=False, default="MXN")

    order = relationship("SalesOrder")


class SalesOrderReturn(Base):
    """One operator-recorded return event against a sales order.

    Marketplaces tell us when a refund was issued (status transition
    + Amazon partial-refund events) but rarely tell us when a
    physical product came back. The operator uses the "Record return"
    dialog on the sales-order detail page to log it; the service
    layer also calls `InventoryService.adjust_stock(+qty,
    reason_code='return')` so the inventory audit catches the credit
    automatically.

    `order_item_id` is nullable because legacy orders may have
    line items whose product_id never mapped — the operator can
    still record the physical return against the product directly.

    `quantity` is always positive (the DB CHECK enforces it). Each
    row is a discrete "N units came back" event; partial returns
    against a 5-unit order line typically produce two or three rows
    over time as the buyer ships items back.

    The breakdown row of the parent order is intentionally NOT
    touched — returns are physical, not financial. The Phase-8
    cost engine's revenue math reflects what the marketplace paid
    us, which is unaffected by whether the customer kept the product
    or not.
    """

    __tablename__ = "sales_order_returns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id = Column(
        Integer,
        ForeignKey("sales_order_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity = Column(Integer, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    recorded_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason = Column(String(500), nullable=True)
    notes = Column(String, nullable=True)  # Text in PG via String

    order = relationship("SalesOrder")
    order_item = relationship("SalesOrderItem")
    product = relationship("Product")


class SalesOrderStatusEvent(Base):
    """Append-only audit of every `SalesOrder.status` transition.

    Both pollers (`mercadolibre_order_ingestion`, `amazon_order_ingestion`)
    and the ML webhook silently overwrite `SalesOrder.status` on every
    update, so without this table we have no way to answer "how many
    orders did we refund last week?" — the refunds dashboard widget
    needs history.

    `from_status` is NULL for the very first event of an order (the
    initial insert). All subsequent events carry both bounds.
    `source_signal` records which ingestion path wrote the event so a
    "poll keeps undoing the webhook" type bug is debuggable from the
    audit alone.

    Insertion is gated on `old != new` — pollers that re-observe the
    same status don't generate noise rows.
    """

    __tablename__ = "sales_order_status_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False, index=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_signal = Column(String(32), nullable=False)

    order = relationship("SalesOrder", back_populates="status_events")
