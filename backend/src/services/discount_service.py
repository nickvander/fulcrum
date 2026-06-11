"""Discount-code validation + management (FP Phase 1).

Fulcrum owns the discount rules + math. ``validate_discount`` is PURE (no
mutation) — the Vendio BFF calls it for the cart preview, and order-create calls
it again under a row lock (``lock=True``) to apply + record the redemption
atomically (Phase 1b). Money is Float pesos. The discount NEVER exceeds the
subtotal (no negative totals).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.discount import DiscountCode, DiscountKind, DiscountRedemption

# Machine-readable invalid reasons (the storefront maps these to localized copy).
REASON_NOT_FOUND = "not_found"
REASON_INACTIVE = "inactive"
REASON_NOT_STARTED = "not_started"
REASON_EXPIRED = "expired"
REASON_BELOW_MIN_SPEND = "below_min_spend"
REASON_MAX_REDEMPTIONS = "max_redemptions"
REASON_PER_CUSTOMER_LIMIT = "per_customer_limit"


@dataclass
class DiscountValidation:
    valid: bool
    reason: str | None = None
    code_id: int | None = None
    kind: str | None = None
    value: float | None = None
    discount_amount: float = 0.0


def normalize_code(code: str | None) -> str:
    return (code or "").strip().upper()


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _aware(dt: datetime.datetime) -> datetime.datetime:
    """Treat a naive DB datetime as UTC so comparisons never raise."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=datetime.timezone.utc)


def compute_discount_amount(kind: str, value: float, subtotal: float) -> float:
    """Discount in Float pesos, rounded to 2dp, capped at the subtotal (>= 0)."""
    sub = round(float(subtotal), 2)
    if sub <= 0:
        return 0.0
    if kind == DiscountKind.PERCENTAGE.value:
        amount = round(sub * float(value) / 100.0, 2)
    else:  # fixed
        amount = round(float(value), 2)
    return max(0.0, min(amount, sub))


def validate_discount(
    db: Session,
    code: str,
    subtotal: float,
    customer_user_id: int | None = None,
    *,
    lock: bool = False,
) -> DiscountValidation:
    """Validate ``code`` against ``subtotal`` (+ optional customer). No mutation.

    When ``lock`` is True the code row is ``SELECT ... FOR UPDATE``-locked so the
    caller (order-create) can count redemptions + insert a new one race-safely.
    """
    normalized = normalize_code(code)
    if not normalized:
        return DiscountValidation(False, REASON_NOT_FOUND)

    query = db.query(DiscountCode).filter(DiscountCode.code == normalized)
    if lock:
        query = query.with_for_update()
    dc = query.first()
    if dc is None:
        return DiscountValidation(False, REASON_NOT_FOUND)
    if not dc.is_active:
        return DiscountValidation(False, REASON_INACTIVE, dc.id)

    now = _utcnow()
    if dc.starts_at is not None and now < _aware(dc.starts_at):
        return DiscountValidation(False, REASON_NOT_STARTED, dc.id)
    if dc.expires_at is not None and now > _aware(dc.expires_at):
        return DiscountValidation(False, REASON_EXPIRED, dc.id)
    if dc.min_spend is not None and round(float(subtotal), 2) < float(dc.min_spend):
        return DiscountValidation(False, REASON_BELOW_MIN_SPEND, dc.id)

    if dc.max_redemptions is not None:
        used = (
            db.query(func.count(DiscountRedemption.id))
            .filter(DiscountRedemption.discount_code_id == dc.id)
            .scalar()
            or 0
        )
        if used >= dc.max_redemptions:
            return DiscountValidation(False, REASON_MAX_REDEMPTIONS, dc.id)

    if dc.per_customer_limit is not None and customer_user_id is not None:
        used_by = (
            db.query(func.count(DiscountRedemption.id))
            .filter(
                DiscountRedemption.discount_code_id == dc.id,
                DiscountRedemption.customer_user_id == customer_user_id,
            )
            .scalar()
            or 0
        )
        if used_by >= dc.per_customer_limit:
            return DiscountValidation(False, REASON_PER_CUSTOMER_LIMIT, dc.id)

    amount = compute_discount_amount(dc.kind, dc.value, subtotal)
    return DiscountValidation(True, None, dc.id, dc.kind, dc.value, amount)


# ---- management (CRUD) — codes are managed in Fulcrum's ops surface ----------


def create_code(db: Session, **fields) -> DiscountCode:
    fields["code"] = normalize_code(fields.get("code"))
    dc = DiscountCode(**fields)
    db.add(dc)
    db.flush()
    return dc


def get_code(db: Session, code_id: int) -> DiscountCode | None:
    return db.query(DiscountCode).filter(DiscountCode.id == code_id).first()


def list_codes(db: Session) -> list[DiscountCode]:
    return db.query(DiscountCode).order_by(DiscountCode.created_at.desc()).all()


def update_code(db: Session, dc: DiscountCode, **fields) -> DiscountCode:
    if "code" in fields and fields["code"] is not None:
        fields["code"] = normalize_code(fields["code"])
    for key, value in fields.items():
        if value is not None or key in ("min_spend", "starts_at", "expires_at",
                                        "max_redemptions", "per_customer_limit", "description"):
            setattr(dc, key, value)
    db.flush()
    return dc


def delete_code(db: Session, dc: DiscountCode) -> None:
    db.delete(dc)
    db.flush()
