import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class InventoryAdjustmentReasonCode(str, enum.Enum):
    """Typed taxonomy for *why* stock moved. Stored as a `String` on
    `InventoryAdjustment.reason_code` (not a PG enum type) to keep
    the add-a-new-code migration a single ALTER instead of a USING
    cast; the CHECK constraint enforces the set at the DB layer.

    Categories:

      - **Operator-initiated investigations** —
        `shrinkage` / `recount` / `damage` / `theft` / `correction`
        / `manual`. These cover the "stock changed and I want to
        record why" workflow on the inventory adjustment dialog.

      - **System-initiated, tied to an order** — `sale`
        (decrement on order ingestion), `cancellation` (credit
        back on cancel-before-ship), `return` (credit back via
        the returns workflow).

      - **System-initiated, tied to a transfer** — `transfer`
        (movement between locations; debit on ship + credit on
        receive).

      - **Catch-all** — `other`, used when an external caller
        doesn't have semantic context. Legacy rows pre-migration
        carry `NULL` in the column, which the audit-page filter
        renders as "uncategorized" — keep the enum free of an
        "uncategorized" value so the NULL semantic is explicit.
    """
    SHRINKAGE = "shrinkage"
    RECOUNT = "recount"
    DAMAGE = "damage"
    RETURN = "return"
    THEFT = "theft"
    CORRECTION = "correction"
    SALE = "sale"
    CANCELLATION = "cancellation"
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    MANUAL = "manual"
    OTHER = "other"

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)  # Allow null for non-variant inventory
    quantity = Column(Integer, default=0)
    location = Column(String, default="default")  # Warehouse location, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    variant = relationship("ProductVariant", back_populates="inventory_items")


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)  # Nullable to support variants
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)  # Nullable to support base products
    adjustment = Column(Integer, nullable=False)  # Positive for additions, negative for subtractions
    reason = Column(String)  # Reason for the adjustment (free-text note from the caller)
    # Typed taxonomy for why stock moved (shrinkage / recount / damage
    # / return / theft / correction / sale / cancellation / transfer /
    # manual / other). The CHECK constraint
    # `ck_inventory_adjustments_reason_code` enforces the set at the DB
    # layer; the audit page filter keys off this column. NULL on legacy
    # rows ingested before the column existed — the audit page renders
    # those as "uncategorized".
    reason_code = Column(String(32), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=True)  # Timestamp of the adjustment
    created_by = Column(String, nullable=False)  # User who made the adjustment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_adjustments")
    variant = relationship("ProductVariant", back_populates="inventory_adjustments")
