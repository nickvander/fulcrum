"""Stock reservations for async (OXXO/SPEI) pending payments.

When the storefront issues an OXXO/SPEI voucher the order is NOT created yet —
the buyer pays out-of-band, sometimes days later. Without a hold, other shoppers
can drain the stock in the meantime, so a buyer who finally pays can't be
fulfilled (money taken, no goods → manual refund). This service holds the stock
for the pending window:

  * ``reserve``  — atomically DECREMENT on-hand (same guarded path as a sale) for
                   each line and record a :class:`StockReservation`. All-or-nothing
                   (one SAVEPOINT); insufficient stock raises so the caller 409s.
                   Idempotent on ``reservation_key``.
  * ``consume``  — at order-create with this key: mark the hold consumed + link the
                   order. NO second decrement (the stock already left at reserve).
  * ``release``  — credit the held stock back (payment expired/failed or swept).
                   Idempotent (a non-active reservation is a no-op).
  * ``sweep_expired`` — release every active reservation past its ``expires_at``.

Audit: reserve writes a SALE adjustment (a reservation is a pending sale),
release a CANCELLATION (mirrors order-cancel re-credit), both tagged with
``source="stock_reservation"`` so they're traceable without a new reason-code
CHECK-constraint migration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from src.models.inventory import (
    InventoryAdjustmentReasonCode,
    StockReservation,
    StockReservationItem,
    StockReservationStatus,
)
from src.services.inventory_service import inventory_service

_RESERVATION_SOURCE = "stock_reservation"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get(db: Session, reservation_key: str) -> Optional[StockReservation]:
    return (
        db.query(StockReservation)
        .filter(StockReservation.reservation_key == reservation_key)
        .first()
    )


def reserve(
    db: Session,
    *,
    reservation_key: str,
    items: Iterable[dict],
    location: str = "default",
    expires_at: Optional[datetime] = None,
) -> StockReservation:
    """Hold stock for ``items`` under ``reservation_key`` (idempotent).

    ``items`` are ``{product_id, variant_id?, quantity}`` dicts. Raises
    ``InsufficientStockError`` (from the atomic decrement) if any line can't be
    held — the SAVEPOINT rolls back the whole reservation. Does NOT commit.
    """
    existing = get(db, reservation_key)
    if existing is not None:
        # Idempotent: a re-issued reserve returns the existing hold rather than
        # decrementing a second time (mirrors order-create idempotency).
        return existing

    with db.begin_nested():
        reservation = StockReservation(
            reservation_key=reservation_key,
            status=StockReservationStatus.ACTIVE.value,
            location=location,
            expires_at=expires_at,
        )
        db.add(reservation)
        db.flush()  # populate reservation.id for the items + audit source_id

        for line in items:
            product_id = int(line["product_id"])
            variant_id = line.get("variant_id")
            variant_id = int(variant_id) if variant_id is not None else None
            quantity = int(line["quantity"])

            db.add(
                StockReservationItem(
                    reservation_id=reservation.id,
                    product_id=product_id,
                    variant_id=variant_id,
                    quantity=quantity,
                )
            )
            # Guarded atomic decrement — RAISES InsufficientStockError if this
            # line can't be held, rolling back the SAVEPOINT (no partial hold).
            inventory_service.decrement_stock_atomic(
                db,
                product_id=product_id,
                quantity=quantity,
                variant_id=variant_id,
                location=location,
                reason=f"oxxo/spei reservation {reservation_key}",
                reason_code=InventoryAdjustmentReasonCode.SALE,
                user_id=_RESERVATION_SOURCE,
                source=_RESERVATION_SOURCE,
                source_id=reservation.id,
            )

    return reservation


def consume(db: Session, reservation_key: str, order_id: int) -> bool:
    """Mark an ACTIVE reservation consumed and link it to ``order_id``.

    Returns True if a consume happened (or was already consumed for this order —
    idempotent), False if there is no active reservation to consume (the caller
    then falls back to a normal decrement). NO stock change: the hold already
    decremented on-hand at reserve time.
    """
    reservation = get(db, reservation_key)
    if reservation is None:
        return False
    if reservation.status == StockReservationStatus.CONSUMED.value:
        # Idempotent: already consumed (e.g. an order-create retry).
        return True
    if reservation.status != StockReservationStatus.ACTIVE.value:
        return False
    reservation.status = StockReservationStatus.CONSUMED.value
    reservation.consumed_at = _now()
    reservation.order_id = order_id
    db.add(reservation)
    return True


def release(db: Session, reservation_key: str) -> Optional[StockReservation]:
    """Release an ACTIVE reservation, crediting the held stock back (idempotent).

    Returns the reservation (any status) or None if the key is unknown. A
    non-active reservation is a no-op (already consumed/released). Does NOT commit.
    """
    reservation = get(db, reservation_key)
    if reservation is None:
        return None
    if reservation.status != StockReservationStatus.ACTIVE.value:
        return reservation

    for item in reservation.items:
        inventory_service.adjust_stock(
            db,
            product_id=item.product_id,
            adjustment=int(item.quantity),
            variant_id=item.variant_id,
            reason=f"oxxo/spei reservation released {reservation.reservation_key}",
            reason_code=InventoryAdjustmentReasonCode.CANCELLATION,
            location=reservation.location,
            user_id=_RESERVATION_SOURCE,
            source=_RESERVATION_SOURCE,
            source_id=reservation.id,
        )
    reservation.status = StockReservationStatus.RELEASED.value
    reservation.released_at = _now()
    db.add(reservation)
    return reservation


def sweep_expired(db: Session, *, now: Optional[datetime] = None) -> int:
    """Release every ACTIVE reservation whose ``expires_at`` is in the past.

    A safety net for the case where the PSP never sends an expiry webhook.
    Returns the number of reservations released. Does NOT commit.
    """
    now = now or _now()
    expired = (
        db.query(StockReservation)
        .filter(
            StockReservation.status == StockReservationStatus.ACTIVE.value,
            StockReservation.expires_at.isnot(None),
            StockReservation.expires_at < now,
        )
        .all()
    )
    for reservation in expired:
        release(db, reservation.reservation_key)
    return len(expired)
