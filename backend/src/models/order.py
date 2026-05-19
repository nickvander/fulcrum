from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
import enum

from .base import Base

class OrderSource(enum.Enum):
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
    source = Column(Enum(OrderSource))
    external_order_id = Column(String)

    items = relationship("SalesOrderItem", back_populates="order")
    cost_breakdown = relationship(
        "OrderCostBreakdown",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
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
        Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False, unique=True,
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
        String(16), nullable=False, default="estimated", server_default="estimated", index=True,
    )
    fees_synced_at = Column(DateTime(timezone=True), nullable=True)

    computed_at = Column(DateTime(timezone=True), nullable=False)

    order = relationship("SalesOrder", back_populates="cost_breakdown")
