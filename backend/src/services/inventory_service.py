from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from src.models.inventory import (
    InventoryAdjustment,
    InventoryAdjustmentReasonCode,
    InventoryAdjustmentSource,
    InventoryItem,
    OPERATOR_REVERSIBLE_REASON_CODES,
)
from src.models.order import SalesOrder, SalesOrderItem


class AdjustmentReversalError(Exception):
    """Raised when an inventory adjustment can't be reversed. `code`
    is a stable machine-readable reason the API layer maps to an HTTP
    status + localized message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InsufficientStockError(Exception):
    """Raised when an atomic stock decrement can't be satisfied because
    the on-hand quantity is below the requested amount (or the location
    has no inventory row). `code` is a stable machine-readable reason the
    API layer maps to an HTTP status + localized message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InventoryService:
    def record_adjustment(
        self,
        db: Session,
        product_id: int,
        adjustment: int,
        variant_id: Optional[int] = None,
        reason: Optional[str] = None,
        reason_code: Optional[InventoryAdjustmentReasonCode] = None,
        location: str = "default",
        user_id: Optional[str] = "system",
        reverses_adjustment_id: Optional[int] = None,
        source: Optional[str] = None,
        source_id: Optional[int] = None,
    ) -> Tuple[InventoryItem, InventoryAdjustment]:
        """Core stock mutation: write one `InventoryAdjustment` audit row
        and update/create the matching `InventoryItem`. Returns BOTH so
        callers that need the audit row (e.g. the reversal flow, which
        links rows together) don't have to re-query for it.

        Most callers want :meth:`adjust_stock`, which returns just the
        item for backward compatibility.
        """
        # 1. Create audit log
        inventory_adjustment = InventoryAdjustment(
            product_id=product_id,
            variant_id=variant_id,
            adjustment=adjustment,
            reason=reason,
            reason_code=(
                reason_code.value
                if isinstance(reason_code, InventoryAdjustmentReasonCode)
                else reason_code
            ),
            # Stamp the location so the shrinkage / reason-code rollup
            # can answer "where am I bleeding stock?" per warehouse
            # without joining back through InventoryItem (which would
            # be ambiguous for multi-location SKUs).
            location=location,
            timestamp=datetime.utcnow(),
            created_by=str(user_id),
            reverses_adjustment_id=reverses_adjustment_id,
            # Structured provenance: lets the stock-history UI linkify the
            # source (e.g. the PO) without string-matching the localized
            # `reason`. Accept an enum or a plain string transparently.
            source=(
                source.value
                if isinstance(source, InventoryAdjustmentSource)
                else source
            ),
            source_id=source_id,
        )
        db.add(inventory_adjustment)

        # 2. Get existing stock record
        existing_inventory = db.query(InventoryItem).filter(
            InventoryItem.product_id == product_id,
            InventoryItem.variant_id == variant_id,
            InventoryItem.location == location
        ).first()

        current_qty = existing_inventory.quantity if existing_inventory else 0
        new_qty = current_qty + adjustment

        # 3. Update or Create InventoryItem
        if existing_inventory:
            existing_inventory.quantity = new_qty
            final_item = existing_inventory
        else:
            final_item = InventoryItem(
                product_id=product_id,
                variant_id=variant_id,
                quantity=new_qty,
                location=location
            )
            db.add(final_item)

        return final_item, inventory_adjustment

    def adjust_stock(
        self,
        db: Session,
        product_id: int,
        adjustment: int,
        variant_id: Optional[int] = None,
        reason: Optional[str] = None,
        reason_code: Optional[InventoryAdjustmentReasonCode] = None,
        location: str = "default",
        user_id: Optional[str] = "system",
        source: Optional[str] = None,
        source_id: Optional[int] = None,
    ) -> InventoryItem:
        """
        Adjust stock for a product at a specific location.
        Creates an audit trail (InventoryAdjustment) and updates/creates the InventoryItem.

        `reason_code` is the typed taxonomy that drives the audit
        filter (shrinkage / recount / damage / return / theft / etc.).
        Callers with semantic context (order ingestion, returns,
        transfers) MUST set it; opaque callers can leave it None and
        the row lands as "uncategorized" in the audit log.

        `source` / `source_id` are the structured provenance of the
        movement (e.g. ``'purchase_order'`` + the PO id). Set them when
        the adjustment originates from an entity the UI should be able to
        deep-link to, so it doesn't have to parse the localized `reason`.
        """
        item, _adjustment = self.record_adjustment(
            db,
            product_id=product_id,
            adjustment=adjustment,
            variant_id=variant_id,
            reason=reason,
            reason_code=reason_code,
            location=location,
            user_id=user_id,
            source=source,
            source_id=source_id,
        )
        return item

    def decrement_stock_atomic(
        self,
        db: Session,
        product_id: int,
        quantity: int,
        variant_id: Optional[int] = None,
        location: str = "default",
        reason: Optional[str] = None,
        reason_code: InventoryAdjustmentReasonCode = InventoryAdjustmentReasonCode.SALE,
        user_id: Optional[str] = "system",
    ) -> InventoryItem:
        """Atomically remove ``quantity`` units of on-hand stock at
        ``location``, REJECTING the operation when fewer than ``quantity``
        units exist.

        Why this exists: :meth:`record_adjustment` is a read-then-write
        (read current qty, compute ``current + adjustment``, write it back)
        with no row lock and no floor guard. Two concurrent sales of the
        last unit can both read ``1`` and both write ``0`` — overselling,
        and nothing stops the value going negative. This method instead
        issues a single conditional statement::

            UPDATE inventory_items
               SET quantity = quantity - :n
             WHERE product_id = :p AND variant_id = :v
               AND location = :loc AND quantity >= :n

        The database evaluates the ``quantity >= :n`` predicate and applies
        the decrement atomically; under concurrency at most one caller can
        claim the last unit, the loser gets ``rowcount == 0`` and is
        rejected. Stock can never go negative. The matching
        ``InventoryAdjustment`` audit row (``-quantity``) is written in the
        SAME transaction. Use this for sales/checkout (online + POS).

        NOTE: request-level idempotency (don't double-decrement when an
        order-create is retried) is layered by the order-create caller
        (FP-04), keyed on the order/line. This primitive guarantees only
        the no-oversell / no-negative invariant.

        Raises :class:`InsufficientStockError`
        (code ``apiErrors.inventory.insufficientStock``) on insufficient
        stock or a missing inventory row, and ``ValueError`` if
        ``quantity`` is not a positive integer.
        """
        if quantity <= 0:
            raise ValueError("decrement quantity must be a positive integer")

        # Atomic, guarded decrement — the WHERE floor is what prevents the
        # read-then-write oversell race. synchronize_session=False because
        # we refresh the returned item from the DB below.
        result = db.execute(
            update(InventoryItem)
            .where(
                InventoryItem.product_id == product_id,
                InventoryItem.variant_id == variant_id,
                InventoryItem.location == location,
                InventoryItem.quantity >= quantity,
            )
            .values(quantity=InventoryItem.quantity - quantity)
            .execution_options(synchronize_session=False)
        )

        if result.rowcount == 0:
            raise InsufficientStockError(
                code="apiErrors.inventory.insufficientStock",
                message=(
                    f"Insufficient stock for product {product_id}"
                    + (f" variant {variant_id}" if variant_id is not None else "")
                    + f" at '{location}': cannot remove {quantity}."
                ),
            )

        # Audit row, in the same transaction as the decrement.
        inventory_adjustment = InventoryAdjustment(
            product_id=product_id,
            variant_id=variant_id,
            adjustment=-quantity,
            reason=reason,
            reason_code=(
                reason_code.value
                if isinstance(reason_code, InventoryAdjustmentReasonCode)
                else reason_code
            ),
            location=location,
            timestamp=datetime.utcnow(),
            created_by=str(user_id),
        )
        db.add(inventory_adjustment)

        item = (
            db.query(InventoryItem)
            .filter(
                InventoryItem.product_id == product_id,
                InventoryItem.variant_id == variant_id,
                InventoryItem.location == location,
            )
            .one()
        )
        # The Core UPDATE bypassed the identity map; refresh to reflect the
        # decremented quantity on the returned ORM object.
        db.refresh(item)
        return item

    def reverse_adjustment(
        self,
        db: Session,
        adjustment_id: int,
        *,
        actor: Optional[str] = "system",
        note: Optional[str] = None,
    ) -> InventoryAdjustment:
        """Undo an operator-entered inventory adjustment by booking an
        equal-and-opposite `correction` row that points back at the
        original.

        Guardrails (each raises `AdjustmentReversalError` with a stable
        code the API maps to 404/409):
          - the original must exist (`not_found`)
          - its reason code must be operator-reversible (`not_reversible`)
            — system/lifecycle rows (sale, cancellation, return, …) are
            owned by their order/PO/transfer workflow
          - it must not itself be a reversal (`is_reversal`)
          - it must not already be reversed (`already_reversed`)

        Does NOT commit — the caller owns the transaction.
        """
        original = (
            db.query(InventoryAdjustment)
            .filter(InventoryAdjustment.id == adjustment_id)
            .first()
        )
        if original is None:
            raise AdjustmentReversalError("not_found", f"Adjustment {adjustment_id} not found")

        if original.reverses_adjustment_id is not None:
            raise AdjustmentReversalError(
                "is_reversal", "A reversal row cannot itself be reversed"
            )

        if (original.reason_code or "") not in OPERATOR_REVERSIBLE_REASON_CODES:
            raise AdjustmentReversalError(
                "not_reversible",
                f"Reason code '{original.reason_code}' is managed by its own "
                "workflow and can't be reversed from the audit log",
            )

        # Idempotency: a unique index also guards this at the DB layer,
        # but checking first lets us return a clean 409 instead of an
        # IntegrityError.
        already = (
            db.query(InventoryAdjustment.id)
            .filter(InventoryAdjustment.reverses_adjustment_id == original.id)
            .first()
        )
        if already is not None:
            raise AdjustmentReversalError(
                "already_reversed", f"Adjustment {adjustment_id} was already reversed"
            )

        note_suffix = f" — {note}" if note else ""
        _item, reversal = self.record_adjustment(
            db,
            product_id=original.product_id,
            adjustment=-original.adjustment,
            variant_id=original.variant_id,
            reason=f"Reversal of adjustment #{original.id}{note_suffix}",
            reason_code=InventoryAdjustmentReasonCode.CORRECTION,
            location=original.location or "default",
            user_id=actor,
            reverses_adjustment_id=original.id,
        )
        db.flush()
        return reversal

    def assemble_bundle(
        self,
        db: Session,
        bundle_id: int,
        quantity: int,
        user_id: Optional[str] = "system"
    ):
        """
        Assembles a bundle by decreasing component stock and increasing bundle stock.
        """
        from sqlalchemy.orm import joinedload
        from src.models.product import Product 

        bundle = db.query(Product).options(joinedload(Product.bundle_components)).filter(Product.id == bundle_id).first()
        if not bundle or not bundle.is_bundle:
             raise ValueError("Product is not a bundle")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if not bundle.bundle_components:
             raise ValueError("Bundle has no components")

        # Verify stock sufficiency first (atomic-ish check)
        for comp in bundle.bundle_components:
            required = comp.quantity * quantity
            stock = db.query(InventoryItem).filter(
                InventoryItem.product_id == comp.component_id,
                InventoryItem.location == "default"
            ).first()
            current = stock.quantity if stock else 0
            if current < required:
                comp_name = comp.component.name if comp.component else f"ID {comp.component_id}"
                raise ValueError(f"Insufficient stock for {comp_name}. Required: {required}, Available: {current}")

        # Execute deductions. Bundle assembly is internal stock movement
        # — components move OUT of inventory and a bundle SKU appears
        # IN inventory; classify as TRANSFER on both legs so the audit
        # paginator can show the two sides together.
        for comp in bundle.bundle_components:
            self.adjust_stock(
                db,
                comp.component_id,
                -(comp.quantity * quantity),
                reason=f"Used for Bundle {bundle.sku or bundle.id}",
                reason_code=InventoryAdjustmentReasonCode.TRANSFER,
                user_id=user_id,
            )

        # Add bundle stock
        self.adjust_stock(
            db,
            bundle_id,
            quantity,
            reason="Bundle Assembly",
            reason_code=InventoryAdjustmentReasonCode.TRANSFER,
            user_id=user_id,
        )

    def calculate_sales_velocity(self, db: Session, product_id: int, days: int = 30) -> float:
        """
        Calculates average daily sales over the last N days.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Query sum of quantity for this product in completed/shipped orders
        # We include COMPLETED, SHIPPED. If statuses differ, adjust here.
        total_sold = db.query(func.sum(SalesOrderItem.quantity)).join(SalesOrder).filter(
            SalesOrderItem.product_id == product_id,
            SalesOrder.created_at >= cutoff_date,
            SalesOrder.status.in_(["COMPLETED", "SHIPPED"]) 
        ).scalar() or 0
        
        return float(total_sold) / float(days)

    def calculate_days_of_inventory(self, db: Session, product_id: int) -> float:
        """
        Calculates estimated days of stock remaining based on sales velocity.
        Returns 999.0 if velocity is 0 (infinite stock relative to sales).
        """
        # Get current stock (sum across all locations)
        stock = db.query(func.sum(InventoryItem.quantity)).filter(
            InventoryItem.product_id == product_id
        ).scalar() or 0
        
        velocity = self.calculate_sales_velocity(db, product_id)
        
        if velocity <= 0:
            return 999.0 
            
        return float(stock) / velocity

    def get_effective_low_inventory_threshold(self, db: Session, product_id: int) -> int:
        """
        Returns the low inventory threshold (days) for a product.
        Checks product specific override first, then falls back to global store setting.
        """
        from src.crud.crud_product_inventory_settings import product_inventory_settings as crud_pis
        from src.crud.crud_store_settings import store_settings as crud_ss
        
        # 1. Check Product Specific
        prod_settings = crud_pis.get_by_product(db, product_id=product_id)
        if prod_settings and prod_settings.low_inventory_days_threshold is not None:
             return prod_settings.low_inventory_days_threshold
             
        # 2. Check Global
        store_settings = crud_ss.get_settings(db)
        return store_settings.low_inventory_days_default

    def get_effective_low_stock_quantity_threshold(self, db: Session, product_id: int) -> int:
        """
        Returns the low stock quantity threshold for a product.
        Checks product specific override first, then falls back to global store setting.
        """
        from src.crud.crud_product_inventory_settings import product_inventory_settings as crud_pis
        from src.crud.crud_store_settings import store_settings as crud_ss
        
        # 1. Check Product Specific
        prod_settings = crud_pis.get_by_product(db, product_id=product_id)
        if prod_settings and prod_settings.low_stock_quantity_threshold is not None:
             return prod_settings.low_stock_quantity_threshold
             
        # 2. Check Global
        store_settings = crud_ss.get_settings(db)
        return store_settings.low_stock_quantity_default

    def get_total_stock_quantity(self, db: Session, product_id: int) -> int:
        from src.models.inventory import InventoryItem
        total_quantity = db.query(func.sum(InventoryItem.quantity)).filter(InventoryItem.product_id == product_id).scalar()
        return total_quantity or 0

inventory_service = InventoryService()
