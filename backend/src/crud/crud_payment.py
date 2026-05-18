from typing import Optional

from sqlalchemy.orm import Session

from src.models.payment import Payment, PaymentStatus


def get(db: Session, *, id: int) -> Optional[Payment]:
    return db.query(Payment).filter(Payment.id == id).first()


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
