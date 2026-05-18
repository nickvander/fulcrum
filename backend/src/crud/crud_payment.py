from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.payment import Payment, PaymentStatus


def get(db: Session, *, id: int) -> Optional[Payment]:
    return db.query(Payment).filter(Payment.id == id).first()


def list_payments(
    db: Session,
    *,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Payment]:
    """List payments ordered newest-first by id. Filterable by status
    (`pending` / `approved` / `rejected` / `refunded` / `cancelled`)
    and by provider — only `mercado_pago` exists today, but the
    filter is wired so a second gateway doesn't need a schema change.
    """
    q = db.query(Payment)
    if status is not None:
        q = q.filter(Payment.status == status)
    if provider is not None:
        q = q.filter(Payment.provider == provider)
    q = q.order_by(Payment.id.desc())
    return q.offset(skip).limit(limit).all()


def count_payments(
    db: Session,
    *,
    status: Optional[str] = None,
    provider: Optional[str] = None,
) -> int:
    q = db.query(Payment)
    if status is not None:
        q = q.filter(Payment.status == status)
    if provider is not None:
        q = q.filter(Payment.provider == provider)
    return q.count()


def get_by_provider_id(
    db: Session, *, provider: str, external_payment_id: str,
) -> Optional[Payment]:
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.external_payment_id == external_payment_id,
        )
        .first()
    )


def create_pending(
    db: Session,
    *,
    sales_order_id: Optional[int],
    user_id: Optional[int],
    amount: float,
    currency: str,
    payer_email: Optional[str],
    provider: str = "mercado_pago",
) -> Payment:
    """Insert a pending Payment row BEFORE we call the provider.

    The row gives us somewhere to land the external_id + raw response
    after the provider call returns, AND gives us a stable internal
    `id` to put in `external_reference` so the provider's webhook can
    tell us which Fulcrum payment a notification belongs to.
    """
    payment = Payment(
        sales_order_id=sales_order_id,
        user_id=user_id,
        provider=provider,
        status=PaymentStatus.PENDING.value,
        amount=amount,
        currency=currency,
        payer_email=payer_email,
    )
    db.add(payment)
    db.flush()  # populate payment.id without committing
    return payment


def apply_provider_result(
    db: Session,
    *,
    payment: Payment,
    external_id: Optional[str],
    status: PaymentStatus,
    raw: dict,
    error_message: Optional[str] = None,
) -> Payment:
    payment.external_payment_id = external_id
    payment.status = status.value
    payment.raw_response = raw
    payment.error_message = error_message
    return payment


def apply_webhook(
    db: Session,
    *,
    payment: Payment,
    status: PaymentStatus,
    payload: dict,
) -> Payment:
    payment.status = status.value
    payment.last_webhook_payload = payload
    return payment
