"""Storefront discount codes (FP — Phase 1).

Fulcrum is the system of record for money + orders + CFDI, so promo codes are
defined, validated, and applied HERE (the Vendio BFF only collects a code and
previews it). A ``DiscountCode`` carries the rule; a ``DiscountRedemption`` is the
ledger row written when a code is consumed on an order — it is the source of
truth for atomic global + per-customer usage limits.

Money is Float pesos (the Vendio BFF converts centavos<->Float at its edge). The
``kind`` enum is intentionally open to extension ('free_shipping' / scoped codes
land in Phase 2) without a breaking migration.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class DiscountKind(str, enum.Enum):
    """How the discount value is interpreted."""

    PERCENTAGE = "percentage"  # value is a percent 0–100 off the eligible subtotal
    FIXED = "fixed"  # value is a fixed peso amount off (capped at the subtotal)


class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id = Column(Integer, primary_key=True, index=True)
    # Stored NORMALIZED (uppercase, trimmed) + unique so lookups are case-insensitive.
    code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    kind = Column(String(32), nullable=False, default=DiscountKind.PERCENTAGE.value)
    value = Column(Float, nullable=False)
    # Optional rules. NULL ⇒ unconstrained.
    min_spend = Column(Float, nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    max_redemptions = Column(Integer, nullable=True)  # NULL = unlimited (global)
    per_customer_limit = Column(Integer, nullable=True)  # NULL = unlimited per customer
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    redemptions = relationship(
        "DiscountRedemption", back_populates="discount_code", cascade="all, delete-orphan"
    )


class DiscountRedemption(Base):
    """One consumption of a code on an order — the usage-limit ledger.

    Written inside the order-create transaction (Phase 1b), so counting these
    rows under a row lock on the parent code enforces ``max_redemptions`` and
    ``per_customer_limit`` race-safely.
    """

    __tablename__ = "discount_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    discount_code_id = Column(
        Integer, ForeignKey("discount_codes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_order_id = Column(
        Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The buyer (User id) when known; NULL for guest/operator orders. Drives the
    # per-customer limit check.
    customer_user_id = Column(Integer, nullable=True, index=True)
    amount = Column(Float, nullable=False)  # discount applied (Float pesos)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    discount_code = relationship("DiscountCode", back_populates="redemptions")
