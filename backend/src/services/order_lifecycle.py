"""Order lifecycle hook — status-transition audit + reversed_at + stock re-credit.

Every ingestion path that touches `SalesOrder.status`
(ML webhook, ML poll, Amazon poll, future manual edits) routes its
status updates through `apply_status_change` instead of mutating the
column directly. That gives us three things in one place:

  1. **Audit row.** A `SalesOrderStatusEvent` is appended whenever
     `old_status != new_status` so the refunds dashboard widget +
     refund-rate alert have history to query. Today both pollers
     overwrite the column on every tick, losing the trail.

  2. **Reversed marker.** When the order transitions OUT of the
     realized-status set, `OrderCostBreakdown.reversed_at` is set so
     the cost-engine rollups stop counting its revenue. Cleared on
     the (rare) transition back into a realized status, so an
     operator-initiated un-cancel cleanly restores it.

  3. **Cancel-before-ship stock re-credit.** When the transition is
     `realized → CANCELLED` AND the audit shows the order was never
     in a shipped state, the line-item quantities are credited back
     to inventory and `SalesOrder.stock_recredited_at` is stamped.
     Idempotent — re-polling a cancelled order can't double-credit.

The four refund / cancel semantics tracked in `MISSING_ITEMS.md`:

  - **Cancel before ship** → re-credit. Held inventory; never sent.
  - **Cancel after ship** → don't re-credit. Product is out the door;
    if it comes back it's a return, which we don't model today.
  - **Refund (money-only)** → don't re-credit. Refunds typically
    leave the order in a non-CANCELLED status (ML payment-only
    refunds, Amazon partial refunds via `RefundEventList`), so they
    don't take this path at all.
  - **Return** → would re-credit. Marketplaces don't report this
    consistently; out of scope.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from src.models.order import (
    OrderCostBreakdown,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatusEvent,
)
from src.services.inventory_service import inventory_service


logger = logging.getLogger(__name__)


# Mirrors `_REALIZED_ORDER_STATUSES` in the cost engine + reports. A
# breakdown's `reversed_at` is set when the order leaves this set and
# cleared when it re-enters.
REALIZED_STATUSES: frozenset[str] = frozenset(
    {"COMPLETED", "SHIPPED", "DELIVERED", "PAID"}
)

# A "shipment" footprint — used by the re-credit gate. If the audit
# ever recorded one of these as `to_status`, the order had physical
# movement at some point and cancellation should NOT credit stock
# back. The set is intentionally narrow: `PAID` alone means the
# marketplace charged the buyer but doesn't imply shipment.
SHIPPED_STATUSES: frozenset[str] = frozenset({"SHIPPED", "DELIVERED"})

CANCELLED_STATUS = "CANCELLED"


def _was_ever_shipped(db: Session, order: SalesOrder) -> bool:
    """True iff the audit history shows this order ever reached a
    shipped/delivered status. Single indexed lookup."""
    return db.query(
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == order.id)
        .filter(SalesOrderStatusEvent.to_status.in_(SHIPPED_STATUSES))
        .exists()
    ).scalar() or False


def _normalize(status: Optional[str]) -> Optional[str]:
    """Uppercase + strip so comparisons are insensitive to the
    formatting differences between ML (`paid`) and Amazon (`Shipped`)
    payloads. Mirrors what the ingestion paths already do before
    setting the column."""
    if status is None:
        return None
    s = status.strip().upper()
    return s or None


def _set_breakdown_reversal(
    db: Session,
    order: SalesOrder,
    *,
    is_realized_new: bool,
    when: datetime,
) -> None:
    """Toggle `OrderCostBreakdown.reversed_at` based on the new
    status. No-op when the breakdown row hasn't been created yet —
    the cost engine writes one inline on first ingestion, so this is
    only `None` on the rare race where the order was just inserted
    and the breakdown upsert failed."""
    breakdown = (
        db.query(OrderCostBreakdown)
        .filter(OrderCostBreakdown.order_id == order.id)
        .first()
    )
    if breakdown is None:
        return
    if is_realized_new:
        # Order transitioned back INTO realized — un-reverse the
        # breakdown so it counts toward current-period rollups again.
        if breakdown.reversed_at is not None:
            breakdown.reversed_at = None
    else:
        # Order transitioned OUT of realized — mark the breakdown
        # reversed (only if it isn't already, so the timestamp
        # reflects the first reversal, not the most recent poll).
        if breakdown.reversed_at is None:
            breakdown.reversed_at = when


def _recredit_stock(
    db: Session,
    order: SalesOrder,
    *,
    when: datetime,
    source_signal: str,
) -> None:
    """Credit each line item's quantity back to inventory. Bumps
    `order.stock_recredited_at` so subsequent calls no-op.

    Caller has already verified the gates (transition is
    realized→CANCELLED, order was never shipped, stock_recredited_at
    is None). This function does the writes and does NOT recheck —
    keep the policy decision in `apply_status_change` so the gate
    is testable in isolation.
    """
    items: Iterable[SalesOrderItem] = order.items or []
    for item in items:
        if item.product_id is None or not item.quantity:
            continue
        try:
            inventory_service.adjust_stock(
                db,
                product_id=item.product_id,
                adjustment=int(item.quantity),
                reason=f"{source_signal}: order {order.external_order_id or order.id} cancelled before ship",
                user_id=source_signal,
            )
        except Exception:  # noqa: BLE001
            # An adjust_stock failure on one line shouldn't block the
            # rest of the order's lines from being credited — log it
            # so the operator can recover manually. The order-level
            # `stock_recredited_at` stamp below ensures we won't
            # retry the successful lines on the next poll.
            logger.exception(
                "stock re-credit failed for order %s item %s",
                order.id, item.id,
            )
    order.stock_recredited_at = when


def apply_status_change(
    db: Session,
    order: SalesOrder,
    *,
    new_status: Optional[str],
    source_signal: str,
    now: Optional[datetime] = None,
) -> bool:
    """Apply a status transition to `order`, write the audit row,
    toggle the breakdown's `reversed_at`, and re-credit stock if the
    transition is cancel-before-ship.

    Returns True when the status actually changed (audit row was
    written), False when the new value matched the old.

    Caller owns the transaction — this function adds to the session
    and flushes for the FK constraint check, but does NOT commit.

    `source_signal` is one of `ml_webhook` | `ml_poll` | `amazon_poll`
    | `manual` and is persisted to `SalesOrderStatusEvent.source_signal`
    so the operator can debug "the poll keeps undoing the webhook"
    type bugs straight from the audit.
    """
    when = now or datetime.now(timezone.utc)
    old_status = _normalize(order.status)
    new_norm = _normalize(new_status)

    if new_norm is None:
        # Defensive — pollers normalize before calling us, but the
        # webhook payload occasionally lacks the field. Leave the
        # row untouched.
        return False

    if old_status == new_norm:
        return False

    # 1. Write the audit row. The from_status uses the *previous*
    # value of `order.status` (which may be NULL for an order
    # freshly inserted in this same transaction — that's correct
    # and matches the schema's nullable from_status).
    db.add(SalesOrderStatusEvent(
        order_id=order.id,
        from_status=old_status,
        to_status=new_norm,
        changed_at=when,
        source_signal=source_signal,
    ))

    # 2. Mutate the order.
    order.status = new_norm

    # 3. Toggle the breakdown's reversal marker.
    is_realized_new = new_norm in REALIZED_STATUSES
    _set_breakdown_reversal(db, order, is_realized_new=is_realized_new, when=when)

    # 4. Cancel-before-ship stock re-credit.
    if (
        new_norm == CANCELLED_STATUS
        and old_status in REALIZED_STATUSES
        and order.stock_recredited_at is None
        and not _was_ever_shipped(db, order)
    ):
        _recredit_stock(db, order, when=when, source_signal=source_signal)

    db.flush()
    return True


def record_initial_status(
    db: Session,
    order: SalesOrder,
    *,
    source_signal: str,
    now: Optional[datetime] = None,
) -> None:
    """Write the very first status-event row for a newly-inserted
    order so the audit captures the starting state. `from_status` is
    NULL on this row by convention.

    Idempotent — called by the ingestion paths right after the
    initial flush. If an event row already exists for this order
    (e.g. webhook + poll race), this no-ops.
    """
    has_event = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == order.id)
        .first()
        is not None
    )
    if has_event:
        return
    new_norm = _normalize(order.status)
    if new_norm is None:
        return
    db.add(SalesOrderStatusEvent(
        order_id=order.id,
        from_status=None,
        to_status=new_norm,
        changed_at=now or datetime.now(timezone.utc),
        source_signal=source_signal,
    ))
    db.flush()
