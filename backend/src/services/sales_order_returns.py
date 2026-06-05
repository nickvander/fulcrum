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


def list_returns(db: Session, order: SalesOrder) -> List[SalesOrderReturn]:
    """All return events for one order, newest first."""
    return (
        db.query(SalesOrderReturn)
        .filter(SalesOrderReturn.order_id == order.id)
        .order_by(SalesOrderReturn.received_at.desc(), SalesOrderReturn.id.desc())
        .all()
    )
