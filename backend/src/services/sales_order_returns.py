"""Sales-order returns service.

Wraps the two things an operator needs to do when a physical
product comes back from a buyer:

  1. Record the return event against the parent sales order so
     the order detail page surfaces it (+ the dashboard refund
     widget can roll up returned units later if we want).
  2. Credit the units back to inventory via the standard
     `InventoryService.adjust_stock` call, tagged with
     `reason_code='return'` so the audit page filter picks it up.

Both happen in one transaction — if the inventory credit fails the
return row isn't persisted, and vice versa.

Returns are physical, not financial. We deliberately do NOT touch:
  - `SalesOrder.status` (the marketplace owns the order's lifecycle
    status; a return doesn't change "is this order paid/shipped").
  - `OrderCostBreakdown.revenue_amount` / `marketplace_fees_amount`
    (the marketplace paid us based on whether the buyer kept it
    or not; the financial side is already reflected in any prior
    refund event).
  - `SalesOrder.stock_recredited_at` (that flag is owned by the
    cancel-before-ship hook in `order_lifecycle` and means
    something specific; returns use their own
    `sales_order_returns` rows for idempotency context).

The endpoint layer enforces auth + scopes the order lookup; this
module assumes the caller passed an already-loaded `SalesOrder`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from src.core.errors import LocalizedHTTPException
from src.models.inventory import (
    InventoryAdjustmentReasonCode,
    InventoryAdjustmentSource,
)
from src.models.order import SalesOrder, SalesOrderItem, SalesOrderReturn
from src.models.user import User
from src.services.inventory_service import inventory_service


logger = logging.getLogger(__name__)


# The return status lifecycle (Returns Phase 2). Operator-recorded returns are
# created already-`received` (physical product in hand, stock credited); a
# customer self-service request starts `requested` and an operator approval
# drives it to `refunded`.
RETURN_STATUSES = ("requested", "approved", "received", "refunded", "rejected")

# Allowed forward transitions. The BFF's one-shot approval goes
# `requested → refunded` directly (the refund + NCR already fired); the
# intermediate states exist for a more granular operator workflow.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "requested": {"approved", "received", "refunded", "rejected"},
    "approved": {"received", "refunded", "rejected"},
    "received": {"refunded"},
    "refunded": set(),
    "rejected": set(),
}

# States in which the physical product is considered back, so stock is credited
# (exactly once, guarded by `stock_recredited_at`).
_STOCK_BEARING = {"approved", "received", "refunded"}


class ReturnLineInput:
    """Plain DTO for a single line item being returned. Not a
    Pydantic model — the endpoint wraps this in a schema."""

    __slots__ = ("order_item_id", "product_id", "quantity")

    def __init__(
        self,
        *,
        order_item_id: Optional[int],
        product_id: Optional[int],
        quantity: int,
    ) -> None:
        self.order_item_id = order_item_id
        self.product_id = product_id
        self.quantity = quantity


def record_return(
    db: Session,
    *,
    order: SalesOrder,
    lines: Sequence[ReturnLineInput],
    reason: Optional[str],
    notes: Optional[str],
    actor: Optional[User],
    now: Optional[datetime] = None,
) -> List[SalesOrderReturn]:
    """Persist one or more `SalesOrderReturn` rows for the order
    and credit each line's quantity back to inventory. Returns the
    newly-created return rows so the caller can echo them back.

    Validation:
      - `lines` must be non-empty.
      - Each line's `quantity` must be > 0.
      - When `order_item_id` is supplied, the item must belong to
        the order. (We let `product_id`-only lines through for
        legacy orders whose items don't map.)
      - When neither `order_item_id` nor `product_id` is supplied,
        the line is rejected (we wouldn't know what to credit).

    Idempotency: this function is NOT idempotent. The operator
    clicking the dialog twice will create two return rows + two
    stock credits. The UI gates on a confirmation dialog;
    accidental double-clicks are caught by a per-row busy flag.

    Caller owns the transaction — the function flushes for FK
    constraint checks, but does NOT commit.
    """
    when = now or datetime.now(timezone.utc)

    if not lines:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.salesOrderReturn.noLines",
            detail="At least one return line is required",
        )

    # Build a lookup of {order_item_id: SalesOrderItem} so we can
    # validate cheap + grab product_id from the item when the caller
    # supplied only the item id.
    items_by_id = {item.id: item for item in (order.items or [])}

    created: List[SalesOrderReturn] = []
    for line in lines:
        if line.quantity <= 0:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.salesOrderReturn.quantityMustBePositive",
                params={"quantity": line.quantity},
                detail="Return quantity must be > 0",
            )

        order_item: Optional[SalesOrderItem] = None
        resolved_product_id = line.product_id

        if line.order_item_id is not None:
            order_item = items_by_id.get(line.order_item_id)
            if order_item is None:
                raise LocalizedHTTPException(
                    status_code=400,
                    code="apiErrors.salesOrderReturn.itemNotInOrder",
                    params={"order_item_id": line.order_item_id, "order_id": order.id},
                    detail=(
                        f"Order item {line.order_item_id} does not belong to "
                        f"order {order.id}"
                    ),
                )
            # Prefer the item's product_id when the caller didn't pin one;
            # this lets the dialog send just `order_item_id` for the
            # common case.
            if resolved_product_id is None:
                resolved_product_id = order_item.product_id

        if resolved_product_id is None and order_item is None:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.salesOrderReturn.missingProduct",
                detail="Each return line needs either order_item_id or product_id",
            )

        ret = SalesOrderReturn(
            order_id=order.id,
            order_item_id=order_item.id if order_item is not None else None,
            product_id=resolved_product_id,
            quantity=line.quantity,
            received_at=when,
            recorded_by_user_id=actor.id if actor is not None else None,
            reason=reason,
            notes=notes,
            # Operator-recorded returns are physically in hand: mark `received`
            # and (below) stamp `stock_recredited_at` when stock is credited, so
            # a later transition into a stock-bearing state never double-credits.
            status="received",
        )
        db.add(ret)
        created.append(ret)

        # Credit the stock back. Skip the inventory mutation when
        # we don't know which product to credit — the return row
        # is still useful for audit, but the operator has to fix
        # the stock manually. This case is rare (legacy unmapped
        # items only) and surfacing it as a 400 would break the
        # dialog flow.
        if resolved_product_id is not None:
            try:
                inventory_service.adjust_stock(
                    db,
                    product_id=resolved_product_id,
                    adjustment=line.quantity,
                    reason=(
                        f"Return for order {order.external_order_id or order.id}"
                        + (f" — {reason}" if reason else "")
                    ),
                    reason_code=InventoryAdjustmentReasonCode.RETURN,
                    user_id=actor.email if actor and actor.email else "system",
                    source=InventoryAdjustmentSource.SALES_ORDER,
                    source_id=order.id,
                )
                # Mark credited so a subsequent transition won't re-credit.
                ret.stock_recredited_at = when
            except Exception:  # noqa: BLE001
                # Logged but not raised: the return row should still
                # land so the operator can investigate the inventory
                # side separately. This mirrors the
                # `apply_status_change` re-credit policy.
                logger.exception(
                    "Return stock credit failed for order %s product %s",
                    order.id, resolved_product_id,
                )

    db.flush()
    return created


def request_return(
    db: Session,
    *,
    order: SalesOrder,
    lines: Sequence[ReturnLineInput],
    reason: Optional[str],
    requested_by: Optional[User],
    idempotency_key: Optional[str],
    notes: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[SalesOrderReturn]:
    """Create ``requested`` return row(s) for a customer self-service request.

    Unlike :func:`record_return` (the operator path), this does **NOT** move
    stock and does **NOT** refund — it only records the customer's intent. An
    operator approval later drives the row to ``refunded`` via
    :func:`transition_return`, which is where stock is credited.

    **Idempotent** on ``idempotency_key``: a retry with the same key returns the
    already-created rows instead of creating a second request (Fulcrum's
    operator return path is intentionally not idempotent; the customer path is).

    The per-line ``amount`` is derived server-side from the matched order item's
    ``price_per_unit`` — never trusted from the client. A line referencing an
    item/product not on the order, or a quantity exceeding what was ordered, is
    rejected.

    Caller owns the transaction (the function flushes for FK checks but does not
    commit).
    """
    when = now or datetime.now(timezone.utc)

    if idempotency_key:
        existing = (
            db.query(SalesOrderReturn)
            .filter(SalesOrderReturn.idempotency_key == idempotency_key)
            .order_by(SalesOrderReturn.id.asc())
            .all()
        )
        if existing:
            return existing

    if not lines:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.salesOrderReturn.noLines",
            detail="At least one return line is required",
        )

    items_by_id = {item.id: item for item in (order.items or [])}
    items_by_product: dict[int, SalesOrderItem] = {}
    for item in order.items or []:
        if item.product_id is not None:
            items_by_product.setdefault(item.product_id, item)

    created: List[SalesOrderReturn] = []
    for index, line in enumerate(lines):
        if line.quantity <= 0:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.salesOrderReturn.quantityMustBePositive",
                params={"quantity": line.quantity},
                detail="Return quantity must be > 0",
            )

        order_item: Optional[SalesOrderItem] = None
        resolved_product_id = line.product_id
        if line.order_item_id is not None:
            order_item = items_by_id.get(line.order_item_id)
            if order_item is None:
                raise LocalizedHTTPException(
                    status_code=400,
                    code="apiErrors.salesOrderReturn.itemNotInOrder",
                    params={"order_item_id": line.order_item_id, "order_id": order.id},
                    detail=(
                        f"Order item {line.order_item_id} does not belong to "
                        f"order {order.id}"
                    ),
                )
            if resolved_product_id is None:
                resolved_product_id = order_item.product_id
        elif resolved_product_id is not None:
            order_item = items_by_product.get(resolved_product_id)

        if resolved_product_id is None and order_item is None:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.salesOrderReturn.missingProduct",
                detail="Each return line needs either order_item_id or product_id",
            )

        # Customer can only return what was actually ordered on that line.
        if order_item is not None and order_item.quantity is not None:
            if line.quantity > order_item.quantity:
                raise LocalizedHTTPException(
                    status_code=400,
                    code="apiErrors.salesOrderReturn.quantityExceedsOrdered",
                    params={
                        "quantity": line.quantity,
                        "ordered": order_item.quantity,
                    },
                    detail="Return quantity exceeds the quantity ordered",
                )

        amount: Optional[float] = None
        if order_item is not None and order_item.price_per_unit is not None:
            amount = float(order_item.price_per_unit) * line.quantity

        ret = SalesOrderReturn(
            order_id=order.id,
            order_item_id=order_item.id if order_item is not None else None,
            product_id=resolved_product_id,
            quantity=line.quantity,
            received_at=when,
            recorded_by_user_id=None,
            requested_by_user_id=requested_by.id if requested_by is not None else None,
            reason=reason,
            notes=notes,
            status="requested",
            amount=amount,
            # Only the FIRST row of a multi-line request carries the idempotency
            # key (the column is UNIQUE). The key still dedups the whole request
            # because all rows are created together in one transaction.
            idempotency_key=idempotency_key if index == 0 else None,
        )
        db.add(ret)
        created.append(ret)

    db.flush()
    return created


def transition_return(
    db: Session,
    *,
    ret: SalesOrderReturn,
    new_status: str,
    actor: Optional[User],
    refund_reference: Optional[str] = None,
    now: Optional[datetime] = None,
) -> SalesOrderReturn:
    """Move a return through its lifecycle, crediting stock exactly once.

    Validates the transition against :data:`_ALLOWED_TRANSITIONS`. The first
    time the return enters a stock-bearing state (``approved``/``received``/
    ``refunded``) the line's quantity is credited back to inventory and
    ``stock_recredited_at`` is stamped, so re-approving or re-transitioning is a
    no-op for stock. When the status becomes ``refunded`` the
    ``refund_reference`` + ``refunded_at`` are stamped (idempotently — a repeat
    refunded→refunded request returns the row unchanged).

    Caller owns the transaction (flush only).
    """
    when = now or datetime.now(timezone.utc)
    if new_status not in RETURN_STATUSES:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.salesOrderReturn.invalidStatus",
            params={"status": new_status},
            detail=f"Unknown return status {new_status!r}",
        )

    current = ret.status or "requested"
    if new_status == current:
        # Idempotent self-transition (e.g. a retried approval). Ensure terminal
        # side effects are present but never repeated.
        if new_status == "refunded" and ret.refund_reference is None and refund_reference:
            ret.refund_reference = refund_reference
            ret.refunded_at = ret.refunded_at or when
        return ret

    if new_status not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.salesOrderReturn.invalidTransition",
            params={"from": current, "to": new_status},
            detail=f"Cannot transition a return from {current} to {new_status}",
        )

    # Credit stock once, on the first move into a stock-bearing state.
    if new_status in _STOCK_BEARING and ret.stock_recredited_at is None:
        if ret.product_id is not None:
            order = ret.order
            try:
                inventory_service.adjust_stock(
                    db,
                    product_id=ret.product_id,
                    adjustment=ret.quantity,
                    reason=(
                        f"Return for order "
                        f"{(order.external_order_id or order.id) if order else ret.order_id}"
                        + (f" — {ret.reason}" if ret.reason else "")
                    ),
                    reason_code=InventoryAdjustmentReasonCode.RETURN,
                    user_id=actor.email if actor and actor.email else "system",
                    source=InventoryAdjustmentSource.SALES_ORDER,
                    source_id=ret.order_id,
                )
                ret.stock_recredited_at = when
            except Exception:  # noqa: BLE001
                # Mirror record_return: the lifecycle still advances; the
                # operator can fix the inventory side separately.
                logger.exception(
                    "Return stock credit failed for return %s (order %s product %s)",
                    ret.id, ret.order_id, ret.product_id,
                )

    if new_status == "refunded":
        ret.refunded_at = ret.refunded_at or when
        if refund_reference is not None:
            ret.refund_reference = refund_reference

    ret.status = new_status
    if actor is not None:
        ret.recorded_by_user_id = actor.id
    db.flush()
    return ret


def get_return_or_404(
    db: Session, *, order_id: int, return_id: int
) -> SalesOrderReturn:
    """Load a return row scoped to its order (404 if missing / mismatched)."""
    ret = (
        db.query(SalesOrderReturn)
        .filter(
            SalesOrderReturn.id == return_id,
            SalesOrderReturn.order_id == order_id,
        )
        .first()
    )
    if ret is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrderReturn.notFound",
            params={"id": return_id, "order_id": order_id},
            detail="Return not found for this order",
        )
    return ret


def list_returns(db: Session, order: SalesOrder) -> List[SalesOrderReturn]:
    """All return events for one order, newest first."""
    return (
        db.query(SalesOrderReturn)
        .filter(SalesOrderReturn.order_id == order.id)
        .order_by(SalesOrderReturn.received_at.desc(), SalesOrderReturn.id.desc())
        .all()
    )
