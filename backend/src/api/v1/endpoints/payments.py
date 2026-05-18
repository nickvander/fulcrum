"""
Payment endpoints — POST /payments to create + charge, GET to read.

The webhook handler lives under `/webhooks/mercadopago` in
`endpoints/webhooks.py` so all gateway notifications share one URL
prefix.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user, get_db
from src.core.errors import LocalizedHTTPException
from src.crud import crud_payment
from src.models.payment import PaymentStatus
from src.models.user import User
from src.schemas.payment import Payment as PaymentSchema
from src.schemas.payment import PaymentCreate, PaymentListResponse
from src.services.mercado_pago import mercado_pago_connector


logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/", response_model=PaymentListResponse)
def list_payments(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status: Optional[str] = Query(
        None,
        description="Filter by canonical status (pending/approved/rejected/refunded/cancelled).",
    ),
    provider: Optional[str] = Query(
        None,
        description="Filter by provider (today: mercado_pago).",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Paginated list of payments, newest-first. Used by the operator
    Payments admin page. Returns a `{items, total}` envelope so the UI
    can render `Showing X of Y` without a second round-trip."""
    items = crud_payment.list_payments(
        db, status=status, provider=provider, skip=skip, limit=limit,
    )
    total = crud_payment.count_payments(db, status=status, provider=provider)
    return PaymentListResponse(items=items, total=total)


@router.post("/", response_model=PaymentSchema)
async def create_payment(
    *,
    db: Session = Depends(get_db),
    body: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Charge a card via Mercado Pago using a frontend-tokenized
    `token`. Persists a `Payment` row before the gateway call so a
    network failure still leaves a retry-able record.

    Flow:
      1. Insert Payment(status=PENDING) → gets an internal id.
      2. Call MP `POST /v1/payments` with the token + amount.
         `external_reference` carries Fulcrum's internal payment id
         so MP webhook deliveries can link back to us.
      3. Persist external_id + provider status onto the row.
      4. Return the canonical Payment row to the caller.
    """
    payment = crud_payment.create_pending(
        db,
        sales_order_id=body.sales_order_id,
        user_id=current_user.id,
        amount=body.amount,
        currency=body.currency,
        payer_email=body.payer_email,
    )

    result = await mercado_pago_connector.create_payment(
        amount=body.amount,
        token=body.token,
        description=body.description,
        payer_email=body.payer_email,
        installments=body.installments,
        payment_method_id=body.payment_method_id,
        external_reference=body.external_reference or str(payment.id),
    )

    status = PaymentStatus.from_mercado_pago(result.status)
    crud_payment.apply_provider_result(
        db, payment=payment,
        external_id=result.external_id,
        status=status,
        raw=result.raw,
        error_message=result.error,
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentSchema)
def get_payment(
    payment_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    payment = crud_payment.get(db, id=payment_id)
    if payment is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.payments.notFound",
            params={"id": payment_id},
            detail="Payment not found",
        )
    return payment
