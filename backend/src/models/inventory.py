import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, backref
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
    MARKETPLACE_SYNC = "marketplace_sync"
    MANUAL = "manual"
    OTHER = "other"


# Reason codes an operator is allowed to *reverse* from the audit log.
# These are the manual / investigation entries a human keys in by hand
# and might mis-enter (wrong delta, wrong SKU). The system-owned codes
# (`sale` / `cancellation` / `return` / `purchase` / `transfer` /
# `marketplace_sync`) are deliberately excluded: they're driven by an
# order / PO / transfer lifecycle that has its own correction path, so
# letting the audit log reverse them out from under that workflow would
# desync stock from the owning entity. A `correction` row (which is
# what a reversal itself records as) is also excluded — you can't
# reverse a reversal.
OPERATOR_REVERSIBLE_REASON_CODES = frozenset(
    {
        InventoryAdjustmentReasonCode.SHRINKAGE.value,
        InventoryAdjustmentReasonCode.RECOUNT.value,
        InventoryAdjustmentReasonCode.DAMAGE.value,
        InventoryAdjustmentReasonCode.THEFT.value,
        InventoryAdjustmentReasonCode.MANUAL.value,
        InventoryAdjustmentReasonCode.OTHER.value,
    }
)


class InventoryAdjustmentSource(str, enum.Enum):
    """Structured `InventoryAdjustment.source` keys — the *origin* of a
    stock movement, so UIs can act on it (e.g. deep-link to the source
    PO / order / transfer) without parsing the localized free-text
    `reason`.

    Unlike `InventoryAdjustmentReasonCode` (a CHECK-constrained operator
    taxonomy), this is an open set: new write paths can add a key without
    a migration.

    `source_id` convention — the id of the entity the operator can open:

      - PURCHASE_ORDER       → PurchaseOrder.id   (receive + receive-correction)
      - STOCK_TRANSFER       → StockTransfer.id   (ship / receive / inbound reconcile)
      - SALES_ORDER          → SalesOrder.id      (sale decrement, cancel re-credit, return)
      - INVENTORY_COUNT      → InventoryCountSession.id (count commit)
      - BUNDLE_ASSEMBLY      → bundle Product.id  (both legs of an assembly)
      - MARKETPLACE_SYNC     → MarketplaceListing.id (or NULL on shell import)
      - ADJUSTMENT_REVERSAL  → the reversed InventoryAdjustment.id

    Returns and cancellations deliberately key on SALES_ORDER (the order
    the operator recognises and can open) rather than their own row id.
    """
    PURCHASE_ORDER = "purchase_order"
    STOCK_TRANSFER = "stock_transfer"
    SALES_ORDER = "sales_order"
    INVENTORY_COUNT = "inventory_count"
    BUNDLE_ASSEMBLY = "bundle_assembly"
    MARKETPLACE_SYNC = "marketplace_sync"
    ADJUSTMENT_REVERSAL = "adjustment_reversal"


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
    # When this row is itself a *reversal* of an earlier adjustment, this
    # points back at the row it undoes (and that row's `reversed_by`
    # backref points here). `unique=True` enforces the idempotency rule
    # at the DB layer: an adjustment can be reversed at most once.
    # NULL for ordinary (non-reversal) rows. ON DELETE SET NULL so a
    # product cascade-delete that removes the original doesn't orphan
    # the reversal.
    reverses_adjustment_id = Column(
        Integer,
        ForeignKey("inventory_adjustments.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    # Structured provenance of the adjustment so UIs can act on its
    # *origin* (e.g. linkify the source PO) without string-matching the
    # localized free-text `reason`. `source` is a stable machine key
    # ('purchase_order', …) and `source_id` the originating entity's id
    # (e.g. `PurchaseOrder.id`). Both NULL on legacy rows and on
    # adjustments with no structured origin (manual edits). Deliberately
    # NOT CHECK-constrained — unlike `reason_code` (a fixed operator
    # taxonomy), `source` should grow with new write paths without a
    # migration each time. Indexed on `source` for "everything that came
    # from PO receiving" style queries.
    source = Column(String(32), nullable=True, index=True)
    source_id = Column(Integer, nullable=True)

    # Relationships
    product = relationship("Product", back_populates="inventory_adjustments")
    variant = relationship("ProductVariant", back_populates="inventory_adjustments")
    # `reverses` → the original row this one undoes; `reversed_by` (the
    # backref on that original) → the reversal row. uselist=False because
    # the unique constraint guarantees at most one reversal per row.
    reverses = relationship(
        "InventoryAdjustment",
        remote_side=[id],
        backref=backref("reversed_by", uselist=False),
    )


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


# --- Stock reservations (OXXO/SPEI pending-payment holds) -------------------


class StockReservationStatus(str, enum.Enum):
    """Lifecycle of a stock reservation.

    ACTIVE   — stock is held (decremented from on-hand) awaiting payment.
    CONSUMED — payment cleared; the reservation was converted into a sales
               order (no re-decrement; the stock already left at reserve time).
    RELEASED — the hold was released (payment expired/failed or swept); the
               held stock was credited back to on-hand.
    """

    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"


class StockReservation(Base):
    """A short-lived hold on stock for an async (OXXO/SPEI) pending payment.

    The BFF reserves stock when it issues a payment voucher so a days-long
    pending window can't oversell. Reserving DECREMENTS on-hand quantity (via
    the same guarded atomic path as a sale) and records this row; releasing
    credits it back; consuming (at order-create with this reservation_key)
    links the order WITHOUT a second decrement. Idempotent on ``reservation_key``.
    """

    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)
    # Caller-supplied idempotency key (the BFF's pending-checkout key). Unique so
    # a re-issued reserve returns the existing hold instead of double-decrementing.
    reservation_key = Column(String(128), nullable=False, unique=True, index=True)
    status = Column(String(16), nullable=False, default=StockReservationStatus.ACTIVE.value, index=True)
    location = Column(String(64), nullable=False, default="default")
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    # Set when the reservation is consumed into an order (audit trail).
    order_id = Column(
        Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    items = relationship(
        "StockReservationItem",
        back_populates="reservation",
        cascade="all, delete-orphan",
    )


class StockReservationItem(Base):
    """One reserved line within a :class:`StockReservation`."""

    __tablename__ = "stock_reservation_items"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(
        Integer, ForeignKey("stock_reservations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id = Column(
        Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True
    )
    quantity = Column(Integer, nullable=False)

    reservation = relationship("StockReservation", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
