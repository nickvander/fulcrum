"""Physical-count session workflow.

Wraps the model + audit-trail logic for the operator's
"count many SKUs at once" surface. The endpoint layer enforces
auth + parses HTTP; this module assumes the caller passed an
already-loaded session.

Lifecycle:

  start_session  ───▶  add_item  ◀──┐
                          │         │
                          ▼         │
                       update_count │
                          │         │
                          ▼         │
                       commit_session
                          │
                          ▼
                       (terminal)

  start_session  ───▶  cancel_session
                          │
                          ▼
                       (terminal)

Commit writes one `InventoryAdjustment` per item where
`counted_quantity` is non-NULL AND differs from
`expected_quantity`. All adjustments carry
`reason_code='recount'` so the audit-page filter "show me every
adjustment from physical counts last month" works out of the box.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from src.core.errors import LocalizedHTTPException
from src.models.inventory import (
    InventoryAdjustmentReasonCode,
    InventoryAdjustmentSource,
    InventoryCountSession,
    InventoryCountSessionItem,
    InventoryCountSessionStatus,
    InventoryItem,
)
from src.models.product import Product
from src.models.user import User
from src.services.inventory_service import inventory_service


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def start_session(
    db: Session,
    *,
    actor: Optional[User],
    location: str = "default",
    notes: Optional[str] = None,
    now: Optional[datetime] = None,
) -> InventoryCountSession:
    """Create a new in_progress session."""
    session = InventoryCountSession(
        status=InventoryCountSessionStatus.IN_PROGRESS.value,
        location=location or "default",
        notes=notes,
        started_at=now or datetime.now(timezone.utc),
        started_by_user_id=actor.id if actor is not None else None,
    )
    db.add(session)
    db.flush()
    return session


def _require_in_progress(session: InventoryCountSession) -> None:
    if session.status != InventoryCountSessionStatus.IN_PROGRESS.value:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.inventoryCount.sessionNotInProgress",
            params={"session_id": session.id, "status": session.status},
            detail=(
                f"Session {session.id} is {session.status}; only in-progress "
                "sessions can be edited"
            ),
        )


def add_item_by_sku(
    db: Session,
    *,
    session: InventoryCountSession,
    sku: str,
) -> InventoryCountSessionItem:
    """Look up the product by SKU, snapshot its current
    `InventoryItem.quantity` at the session's location, and
    insert one `InventoryCountSessionItem` row.

    Errors:
      - 404 when the SKU doesn't map to a product.
      - 409 when the session is not `in_progress`.
      - 409 when the SKU is already in the session (unique constraint
        on `(session_id, product_id, variant_id)`).
    """
    _require_in_progress(session)

    sku_clean = (sku or "").strip()
    if not sku_clean:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.inventoryCount.skuRequired",
            detail="SKU is required",
        )

    product = db.query(Product).filter(Product.sku == sku_clean).first()
    if product is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.product.notFoundBySku",
            params={"sku": sku_clean},
            detail=f"No product found with SKU {sku_clean}",
        )

    existing = (
        db.query(InventoryCountSessionItem)
        .filter(InventoryCountSessionItem.session_id == session.id)
        .filter(InventoryCountSessionItem.product_id == product.id)
        .filter(InventoryCountSessionItem.variant_id.is_(None))
        .first()
    )
    if existing is not None:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.inventoryCount.skuAlreadyInSession",
            params={"sku": sku_clean},
            detail=f"SKU {sku_clean} is already in this session",
        )

    # Snapshot expected qty at this session's location. If no
    # InventoryItem row exists for the location yet, treat expected
    # as 0 — the count itself will create the inventory record on
    # commit (via the inventory_service.adjust_stock helper).
    expected = (
        db.query(InventoryItem.quantity)
        .filter(InventoryItem.product_id == product.id)
        .filter(InventoryItem.location == session.location)
        .filter(InventoryItem.variant_id.is_(None))
        .scalar()
    )
    item = InventoryCountSessionItem(
        session_id=session.id,
        product_id=product.id,
        variant_id=None,
        expected_quantity=int(expected or 0),
        counted_quantity=None,
        added_at=datetime.now(timezone.utc),
    )
    db.add(item)
    db.flush()
    return item


def update_count(
    db: Session,
    *,
    session: InventoryCountSession,
    item_id: int,
    counted_quantity: Optional[int],
) -> InventoryCountSessionItem:
    """Set the operator's physical count for one row. Pass `None`
    to clear (operator scanned a SKU but hasn't counted it yet).
    Negative counts are rejected — physical inventory can't go
    below zero.
    """
    _require_in_progress(session)

    if counted_quantity is not None and counted_quantity < 0:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.inventoryCount.negativeCount",
            params={"counted": counted_quantity},
            detail="Counted quantity cannot be negative",
        )

    item = (
        db.query(InventoryCountSessionItem)
        .filter(InventoryCountSessionItem.id == item_id)
        .filter(InventoryCountSessionItem.session_id == session.id)
        .first()
    )
    if item is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.inventoryCount.itemNotFound",
            params={"item_id": item_id, "session_id": session.id},
            detail=f"Item {item_id} not found in session {session.id}",
        )

    item.counted_quantity = counted_quantity
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    return item


def remove_item(
    db: Session,
    *,
    session: InventoryCountSession,
    item_id: int,
) -> None:
    """Drop a row the operator added by mistake. Only legal on
    in-progress sessions."""
    _require_in_progress(session)
    item = (
        db.query(InventoryCountSessionItem)
        .filter(InventoryCountSessionItem.id == item_id)
        .filter(InventoryCountSessionItem.session_id == session.id)
        .first()
    )
    if item is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.inventoryCount.itemNotFound",
            params={"item_id": item_id, "session_id": session.id},
            detail=f"Item {item_id} not found in session {session.id}",
        )
    db.delete(item)
    db.flush()


# ---------------------------------------------------------------------------
# Commit / cancel
# ---------------------------------------------------------------------------


def commit_session(
    db: Session,
    *,
    session: InventoryCountSession,
    actor: Optional[User],
    now: Optional[datetime] = None,
) -> Tuple[int, int]:
    """Commit the session: for each item with a non-NULL
    `counted_quantity`, write an `InventoryAdjustment` with
    `reason_code='recount'` and delta = counted - expected
    (skipping zero-delta rows). Flip the session to `COMMITTED`.

    Returns `(adjustments_created, items_skipped)`:
      - `adjustments_created`: number of audit rows written.
      - `items_skipped`: rows skipped because either `counted_quantity`
        was NULL or `delta == 0` (no change needed).

    Idempotent on a `COMMITTED` session — re-call returns `(0, 0)`
    without writing duplicates because the status guard refuses
    the operation. (Strictly speaking the function returns the
    fresh summary from `_require_in_progress` raising; the
    endpoint layer catches and surfaces "already committed".)
    """
    _require_in_progress(session)

    when = now or datetime.now(timezone.utc)
    user_label = actor.email if actor and actor.email else "system"

    adjustments_created = 0
    items_skipped = 0
    for item in session.items:
        if item.counted_quantity is None:
            items_skipped += 1
            continue
        delta = int(item.counted_quantity) - int(item.expected_quantity or 0)
        if delta == 0:
            items_skipped += 1
            continue
        inventory_service.adjust_stock(
            db,
            product_id=item.product_id,
            adjustment=delta,
            variant_id=item.variant_id,
            reason=f"Physical count session #{session.id}",
            reason_code=InventoryAdjustmentReasonCode.RECOUNT,
            location=session.location,
            user_id=user_label,
            source=InventoryAdjustmentSource.INVENTORY_COUNT,
            source_id=session.id,
        )
        adjustments_created += 1

    session.status = InventoryCountSessionStatus.COMMITTED.value
    session.ended_at = when
    db.flush()
    return adjustments_created, items_skipped


def cancel_session(
    db: Session,
    *,
    session: InventoryCountSession,
    now: Optional[datetime] = None,
) -> InventoryCountSession:
    """Discard the session without writing any adjustments. The
    row stays in the DB so the operator can review their abandoned
    sessions, but it has no inventory effect."""
    _require_in_progress(session)
    session.status = InventoryCountSessionStatus.CANCELLED.value
    session.ended_at = now or datetime.now(timezone.utc)
    db.flush()
    return session


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def list_sessions(
    db: Session,
    *,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[InventoryCountSession]:
    """List sessions newest-first. Optional `status` filter narrows
    to `in_progress` / `committed` / `cancelled`."""
    q = db.query(InventoryCountSession)
    if status is not None:
        q = q.filter(InventoryCountSession.status == status)
    return q.order_by(
        InventoryCountSession.started_at.desc(),
        InventoryCountSession.id.desc(),
    ).limit(limit).all()


def get_session_or_404(db: Session, session_id: int) -> InventoryCountSession:
    session = (
        db.query(InventoryCountSession)
        .filter(InventoryCountSession.id == session_id)
        .first()
    )
    if session is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.inventoryCount.sessionNotFound",
            params={"session_id": session_id},
            detail=f"Count session {session_id} not found",
        )
    return session
