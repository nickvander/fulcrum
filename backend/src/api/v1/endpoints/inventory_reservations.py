"""Stock reservation endpoints (OXXO/SPEI pending-payment holds).

Server-to-server only (the storefront BFF), so they accept the dual
JWT-or-X-API-Key auth. The BFF reserves stock when it issues a voucher, releases
on expiry/failure, and (via order-create's ``reservation_key``) consumes the hold
on payment. A ``sweep-expired`` endpoint lets a cron release stale holds if the
PSP never sends an expiry webhook.
"""
from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.api import dependencies
from src.core.errors import LocalizedHTTPException
from src.models.user import User
from src.services import stock_reservation_service
from src.services.inventory_service import InsufficientStockError
from src.services.stock_reservation_service import _now

router = APIRouter()


class ReservationLineIn(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)


class ReservationCreate(BaseModel):
    reservation_key: str = Field(..., min_length=1, max_length=128)
    items: List[ReservationLineIn] = Field(..., min_length=1)
    location: str = "default"
    expires_in_seconds: Optional[int] = Field(default=None, ge=1)


class ReservationItemOut(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    model_config = ConfigDict(from_attributes=True)


class ReservationOut(BaseModel):
    reservation_key: str
    status: str
    location: str
    expires_at: Optional[str] = None
    order_id: Optional[int] = None
    items: List[ReservationItemOut] = []

    @classmethod
    def of(cls, reservation) -> "ReservationOut":
        return cls(
            reservation_key=reservation.reservation_key,
            status=reservation.status,
            location=reservation.location,
            expires_at=(reservation.expires_at.isoformat() if reservation.expires_at else None),
            order_id=reservation.order_id,
            items=[ReservationItemOut.model_validate(i) for i in reservation.items],
        )


class SweepResult(BaseModel):
    released: int


@router.post("/reservations", response_model=ReservationOut, status_code=201)
def create_reservation(
    *,
    db: Session = Depends(dependencies.get_db),
    payload: ReservationCreate,
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
) -> ReservationOut:
    """Hold stock for the lines (idempotent on ``reservation_key``).

    Insufficient stock for any line → 409, all-or-nothing (no partial hold).
    """
    expires_at = (
        _now() + timedelta(seconds=payload.expires_in_seconds)
        if payload.expires_in_seconds
        else None
    )
    try:
        reservation = stock_reservation_service.reserve(
            db,
            reservation_key=payload.reservation_key,
            items=[line.model_dump() for line in payload.items],
            location=payload.location,
            expires_at=expires_at,
        )
    except InsufficientStockError as exc:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.inventory.insufficientStock",
            params={"key": payload.reservation_key},
            detail=str(exc),
        )
    db.flush()
    return ReservationOut.of(reservation)


@router.get("/reservations/{reservation_key}", response_model=ReservationOut)
def get_reservation(
    *,
    db: Session = Depends(dependencies.get_db),
    reservation_key: str,
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
) -> ReservationOut:
    reservation = stock_reservation_service.get(db, reservation_key)
    if reservation is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.inventory.reservationNotFound",
            params={"key": reservation_key},
            detail=f"No reservation {reservation_key}.",
        )
    return ReservationOut.of(reservation)


@router.post("/reservations/{reservation_key}/release", response_model=ReservationOut)
def release_reservation(
    *,
    db: Session = Depends(dependencies.get_db),
    reservation_key: str,
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
) -> ReservationOut:
    """Release a hold, crediting stock back (idempotent; 404 if unknown)."""
    reservation = stock_reservation_service.release(db, reservation_key)
    if reservation is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.inventory.reservationNotFound",
            params={"key": reservation_key},
            detail=f"No reservation {reservation_key}.",
        )
    return ReservationOut.of(reservation)


@router.post("/reservations/sweep-expired", response_model=SweepResult)
def sweep_expired_reservations(
    *,
    db: Session = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
) -> SweepResult:
    """Release every active reservation past its expiry (cron safety net)."""
    return SweepResult(released=stock_reservation_service.sweep_expired(db))
