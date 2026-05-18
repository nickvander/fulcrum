from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PaymentCreate(BaseModel):
    """Body for POST /api/v1/payments.

    `token` is the MP-side card token produced by the frontend SDK. We
    never see raw card data — the token is the only thing the backend
    needs to charge the card.

    `sales_order_id` is the canonical Fulcrum SalesOrder this payment
    settles. May be NULL for ad-hoc payments not tied to an order yet
    (e.g. a future "Pay this invoice" link).
    """
    sales_order_id: Optional[int] = None
    token: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = "MXN"
    description: str = "Fulcrum order"
    payer_email: EmailStr
    installments: int = Field(default=1, ge=1, le=24)
    payment_method_id: Optional[str] = None
    external_reference: Optional[str] = None


class Payment(BaseModel):
    """Read shape returned by GET /api/v1/payments/{id} and the create
    endpoint."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    sales_order_id: Optional[int] = None
    user_id: Optional[int] = None
    provider: str
    external_payment_id: Optional[str] = None
    status: str
    amount: float
    currency: str
    payer_email: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    last_webhook_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaymentListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/payments.

    `total` is the count BEFORE skip/limit so the operator UI can
    render `Showing N–M of Total` without a second request.
    """
    items: List[Payment]
    total: int


class WebhookAck(BaseModel):
    """All gateway webhook handlers return this — MP only needs a
    200/202 to consider the notification delivered."""
    status: str = "received"
