import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    # Warehouse / shelf the adjustment happened at. Mirrors
    # InventoryItem.location so the shrinkage report can answer
    # "where am I bleeding stock?" per-location. NULL on legacy rows
    # ingested before the column existed — the report surfaces those
    # under a "(unknown)" sentinel.
    location = Column(String(64), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=True)  # Timestamp of the adjustment
    created_by = Column(String, nullable=False)  # User who made the adjustment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_adjustments")
    variant = relationship("ProductVariant", back_populates="inventory_adjustments")


class InventoryCountSessionStatus(str, enum.Enum):
    """Lifecycle of an `InventoryCountSession`. Linear:
    `IN_PROGRESS` → `COMMITTED` | `CANCELLED`. Both end-states are
    terminal; a committed session has written its
    `InventoryAdjustment` rows, a cancelled session is a no-op
    audit record so the operator's "I started and walked away"
    history isn't lost."""
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    CANCELLED = "cancelled"


class InventoryCountSession(Base):
    """One operator-led physical count of stock.

    Scoped to a single `location` so multi-warehouse workspaces
    don't double-count a SKU stored in two places. The header
    row tracks the lifecycle (in_progress → committed | cancelled);
    detail rows live in `InventoryCountSessionItem`.

    Commit policy:
      - Iterates every detail row where `counted_quantity IS NOT NULL`.
      - Computes `delta = counted_quantity - expected_quantity`.
      - When `delta != 0`, writes an `InventoryAdjustment` with
        `reason_code='recount'` and a reason referencing the
        session id.
      - Sets the session's `status = COMMITTED` and `ended_at = now`.
      - Idempotent on a `COMMITTED` session — re-calling returns
        the existing summary without writing duplicate adjustments
        (gated on `status` not being `IN_PROGRESS`).
    """
    __tablename__ = "inventory_count_sessions"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(16), nullable=False, default="in_progress", server_default="in_progress")
    location = Column(String(64), nullable=False, default="default", server_default="default")
    notes = Column(String(1000), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    started_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    items = relationship(
        "InventoryCountSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InventoryCountSessionItem.added_at",
    )


class InventoryCountSessionItem(Base):
    """One SKU within a count session.

    `expected_quantity` is a snapshot from `InventoryItem.quantity`
    at add-time. If stock moves between the operator adding the SKU
    and committing the session, the snapshot remains — same as a
    paper count form where the operator wrote down "system says
    50" when they started counting.

    `counted_quantity` is NULL until the operator enters their
    physical count. Commit ignores NULL rows (operator added the
    SKU but didn't count it yet — no adjustment) so an in-progress
    count can be saved and resumed without writing wrong adjustments.
    """
    __tablename__ = "inventory_count_session_items"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "product_id", "variant_id",
            name="uq_inventory_count_session_items_sku",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("inventory_count_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_id = Column(
        Integer, ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
    )
    expected_quantity = Column(Integer, nullable=False)
    counted_quantity = Column(Integer, nullable=True)
    added_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("InventoryCountSession", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
