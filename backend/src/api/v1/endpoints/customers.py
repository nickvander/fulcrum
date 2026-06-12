"""Customer self-service accounts (FP-05).

A storefront-facing router that lets customers register, sign in via a
passwordless magic link, manage their own profile, and manage their own
addresses. It reuses the existing ``User`` and ``Address`` models, the
``crud.user`` / ``crud.address`` CRUD layers, the password hashing and JWT
creation from ``src.core.security``, and the ``password_reset_tokens`` table
(via ``crud.password_reset_token``) as the single-use, short-lived token
mechanism backing the magic link. No new tables / migrations are introduced.
"""
from datetime import timedelta
from typing import List

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src import crud, models
from src.api import dependencies
from src.config import settings
from src.core import security
from src.core.errors import LocalizedHTTPException
from src.core.ratelimit import limiter
from src.models import order as order_models
from src.schemas import address as address_schema
from src.schemas import customer as customer_schema
from src.schemas import sales_order as sales_order_schema
from src.schemas.user import UserCreate, UserType

router = APIRouter()
logger = logging.getLogger(__name__)


def _magic_link_limit() -> str:
    """Per-IP limit for the magic-link endpoints (FP-11). Effectively disabled
    under tests so the suite's repeated calls don't trip it."""
    return "100000/minute" if settings.TESTING else settings.MAGIC_LINK_RATE_LIMIT


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=customer_schema.CustomerProfile,
    tags=["customers"],
)
def register_customer(
    *,
    db: Session = Depends(dependencies.get_db),
    customer_in: customer_schema.CustomerRegister,
) -> customer_schema.CustomerProfile:
    """Self-service registration. Always creates a ``customer`` user."""
    existing = crud.user.get_by_email(db, email=customer_in.email)
    if existing:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.customer.emailExists",
            params={"email": customer_in.email},
            detail="A customer with this email already exists",
        )

    user_in = UserCreate(
        email=customer_in.email,
        password=customer_in.password,
        first_name=customer_in.first_name,
        last_name=customer_in.last_name,
        user_type=UserType.customer,
    )
    user = crud.user.create(db, obj_in=user_in)
    db.commit()
    db.refresh(user)
    return customer_schema.CustomerProfile.from_orm(user)


# ---------------------------------------------------------------------------
# Magic link (passwordless)
# ---------------------------------------------------------------------------
@router.post("/magic-link/request", tags=["customers"])
@limiter.limit(_magic_link_limit)
def request_magic_link(
    request: Request,
    *,
    db: Session = Depends(dependencies.get_db),
    magic_in: customer_schema.MagicLinkRequest,
) -> dict:
    """Request a passwordless sign-in link.

    Reuses the password-reset-token table for a short-lived single-use token.
    Always returns 200 so callers cannot probe which emails are registered.
    """
    user = crud.user.get_by_email(db, email=magic_in.email)
    # Only issue links for active customer accounts, but never reveal that.
    if user and user.is_active and user.user_type == "customer":
        token = crud.password_reset_token.create_reset_token(db, user_id=user.id)
        # Stub "email": log a dev link. In production this would be sent via the
        # email service and the raw token would NOT be logged.
        logger.info(
            "Magic-link issued for customer %s (token tail …%s)",
            user.email,
            token.token[-6:],
        )
    return {"message": "If the email exists, a sign-in link has been sent"}


@router.post(
    "/magic-link/verify",
    response_model=customer_schema.MagicLinkToken,
    tags=["customers"],
)
@limiter.limit(_magic_link_limit)
def verify_magic_link(
    request: Request,
    *,
    db: Session = Depends(dependencies.get_db),
    verify_in: customer_schema.MagicLinkVerify,
) -> dict:
    """Validate and consume a magic-link token, returning an access JWT."""
    reset_token = crud.password_reset_token.get_valid_token(db, token=verify_in.token)
    if not reset_token or reset_token.used:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.customer.magicLinkInvalid",
            detail="Invalid or expired sign-in link",
        )

    user = reset_token.user
    if not user or not user.is_active or user.user_type != "customer":
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.customer.magicLinkInvalid",
            detail="Invalid or expired sign-in link",
        )

    # Consume the single-use token before issuing the session.
    crud.password_reset_token.mark_token_as_used(db, token=reset_token)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=customer_schema.CustomerProfile,
    tags=["customers"],
)
def read_me(
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> customer_schema.CustomerProfile:
    """Return the authenticated customer's safe profile."""
    return customer_schema.CustomerProfile.from_orm(current_user)


@router.patch(
    "/me",
    response_model=customer_schema.CustomerProfile,
    tags=["customers"],
)
@router.put(
    "/me",
    response_model=customer_schema.CustomerProfile,
    tags=["customers"],
)
def update_me(
    *,
    db: Session = Depends(dependencies.get_db),
    customer_in: customer_schema.CustomerUpdate,
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> customer_schema.CustomerProfile:
    """Update the authenticated customer's own profile.

    Persists ``first_name`` / ``last_name`` / ``phone`` / ``whatsapp_opt_in``.
    Toggling ``whatsapp_opt_in`` stamps ``whatsapp_opt_in_at`` server-side (the
    customer can record consent but not forge its timestamp).
    """
    from datetime import datetime, timezone

    update_data = customer_in.model_dump(exclude_unset=True)
    persistable = {
        k: v
        for k, v in update_data.items()
        if k in {"first_name", "last_name", "phone"}
    }
    for field, value in persistable.items():
        setattr(current_user, field, value)

    # Consent: stamp the change time server-side whenever the flag actually flips.
    if "whatsapp_opt_in" in update_data:
        new_opt_in = bool(update_data["whatsapp_opt_in"])
        if new_opt_in != bool(current_user.whatsapp_opt_in):
            current_user.whatsapp_opt_in = new_opt_in
            current_user.whatsapp_opt_in_at = datetime.now(timezone.utc)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return customer_schema.CustomerProfile.from_orm(current_user)


# ---------------------------------------------------------------------------
# Addresses (scoped to the authenticated customer)
# ---------------------------------------------------------------------------
def _get_own_address(
    db: Session, *, address_id: int, user_id: int
) -> models.Address:
    """Fetch an address that must belong to ``user_id`` or raise 404."""
    address = crud.address.get(db, id=address_id)
    if not address or address.user_id != user_id:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.customer.addressNotFound",
            params={"id": address_id},
            detail="Address not found",
        )
    return address


@router.get(
    "/me/addresses",
    response_model=List[address_schema.Address],
    tags=["customers"],
)
def list_my_addresses(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> List[models.Address]:
    return crud.address.get_by_user(db, user_id=current_user.id)


@router.post(
    "/me/addresses",
    response_model=address_schema.Address,
    tags=["customers"],
)
def create_my_address(
    *,
    db: Session = Depends(dependencies.get_db),
    address_in: address_schema.AddressCreate,
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> models.Address:
    db_obj = models.Address(
        street=address_in.street,
        city=address_in.city,
        state=address_in.state,
        postal_code=address_in.postal_code,
        country=address_in.country,
        colonia=address_in.colonia,
        interior=address_in.interior,
        recipient_name=address_in.recipient_name,
        phone=address_in.phone,
        is_primary=address_in.is_primary,
        is_billing=address_in.is_billing,
        is_shipping=address_in.is_shipping,
        user_id=current_user.id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put(
    "/me/addresses/{address_id}",
    response_model=address_schema.Address,
    tags=["customers"],
)
def update_my_address(
    *,
    db: Session = Depends(dependencies.get_db),
    address_id: int,
    address_in: address_schema.AddressUpdate,
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> models.Address:
    address = _get_own_address(db, address_id=address_id, user_id=current_user.id)
    if address_in.is_primary:
        crud.address.set_primary_for_user(
            db, user_id=current_user.id, address_id=address_id
        )
    return crud.address.update(db, db_obj=address, obj_in=address_in)


@router.delete("/me/addresses/{address_id}", tags=["customers"])
def delete_my_address(
    address_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> dict:
    _get_own_address(db, address_id=address_id, user_id=current_user.id)
    crud.address.remove(db, id=address_id)
    return {"message": "Address deleted successfully"}


# ---------------------------------------------------------------------------
# WhatsApp consent — honor an inbound STOP (server-to-server / BFF only)
# ---------------------------------------------------------------------------
@router.post(
    "/whatsapp-opt-out",
    response_model=customer_schema.WhatsAppOptOutResult,
    tags=["customers"],
)
def whatsapp_opt_out(
    *,
    db: Session = Depends(dependencies.get_db),
    payload: customer_schema.WhatsAppOptOutRequest,
    # Server-to-server only: the storefront BFF calls this from its WhatsApp
    # webhook (X-API-Key). NOT a customer-facing endpoint — it must never become
    # a phone→customer enumeration oracle, so it returns only a count. Write →
    # gated against read-only keys.
    current_user: models.User = Depends(dependencies.require_write_scope),
) -> customer_schema.WhatsAppOptOutResult:
    """Clear WhatsApp consent for the customer(s) matching ``phone``.

    Triggered by an inbound STOP forwarded by the BFF. Matches on the last 10
    digits of the phone and opts out every matching customer (honoring a STOP is
    the safe direction). Idempotent; returns the number of records updated. The
    phone is never logged.
    """
    from src.services.whatsapp_consent import opt_out_by_phone

    updated = opt_out_by_phone(db, payload.phone)
    return customer_schema.WhatsAppOptOutResult(updated=updated)


# ---------------------------------------------------------------------------
# Customer self-service orders + returns (Returns Phase 2)
# ---------------------------------------------------------------------------
#
# Ownership-scoped: these resolve the customer from the session JWT
# (`get_current_customer`) and only ever touch an order whose
# `customer_user_id` matches. They are intentionally SEPARATE from the
# operator `/sales-orders/{id}/returns` endpoints, which do NO ownership check
# (reusing those for customers would let any signed-in customer act on any
# order — see returns-rma.md §2). Cost/margin fields are never serialized here.


def _load_owned_order_or_404(
    db: Session, order_id: int, customer: "models.User"
) -> "order_models.SalesOrder":
    """Load an order the customer OWNS, or 404. A non-owner (incl. an order with
    a NULL `customer_user_id`, i.e. an operator/marketplace order) gets the SAME
    404 as a missing id — never a 403 — so the endpoint isn't an existence
    oracle for orders the customer doesn't own."""
    from sqlalchemy.orm import joinedload

    order = (
        db.query(order_models.SalesOrder)
        .options(joinedload(order_models.SalesOrder.items))
        .filter(order_models.SalesOrder.id == order_id)
        .first()
    )
    if order is None or order.customer_user_id != customer.id:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrder.notFound",
            params={"id": order_id},
            detail="Sales order not found",
        )
    return order


def _customer_return_read(ret: "order_models.SalesOrderReturn") -> "sales_order_schema.CustomerReturnRead":
    product = ret.product
    return sales_order_schema.CustomerReturnRead(
        id=ret.id,
        order_id=ret.order_id,
        order_item_id=ret.order_item_id,
        product_id=ret.product_id,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        quantity=ret.quantity,
        status=ret.status or "requested",
        reason=ret.reason,
        amount=ret.amount,
        requested_at=ret.received_at,
        refunded_at=ret.refunded_at,
        restock=ret.restock,
    )


def _customer_order_detail(
    db: Session, order: "order_models.SalesOrder"
) -> "sales_order_schema.CustomerOrderDetail":
    """Build the cost-stripped customer view of an order + its returns."""
    items = []
    for item in order.items or []:
        product = item.product
        items.append(
            sales_order_schema.CustomerOrderItem(
                id=item.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                price_per_unit=item.price_per_unit,
                product_name=product.name if product else None,
                product_sku=product.sku if product else None,
            )
        )
    from src.config import settings
    from src.services.sales_order_returns import (
        is_order_status_returnable,
        is_within_return_window,
        list_returns as svc_list_returns,
        remaining_returnable_by_item,
    )

    return_rows = svc_list_returns(db, order)
    returns = [_customer_return_read(r) for r in return_rows]

    # Eligibility (Phase 2), computed authoritatively so the storefront can gate
    # the request form. Block reason precedence: closed order > window expired >
    # nothing left to return.
    window_days = settings.RETURN_WINDOW_DAYS
    remaining = remaining_returnable_by_item(order, return_rows)
    block_reason: str | None = None
    if not is_order_status_returnable(order):
        block_reason = "order_closed"
    elif not is_within_return_window(order):
        block_reason = "window_expired"
    elif not remaining:
        block_reason = "fully_returned"

    # Ship-to (FP-B): serialize only when the order carries one at all —
    # POS/marketplace/legacy orders stay `ship_to: null` rather than an
    # all-null object.
    ship_to_values = {
        field: getattr(order, f"ship_to_{field}")
        for field in (
            "name",
            "street",
            "colonia",
            "interior",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
        )
    }
    ship_to = (
        sales_order_schema.OrderShipTo(**ship_to_values)
        if any(v is not None for v in ship_to_values.values())
        else None
    )

    return sales_order_schema.CustomerOrderDetail(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        currency=order.currency,
        created_at=order.created_at,
        # Buyer-facing fulfillment (FP-A): carrier + tracking only — the label
        # asset URL and shipping internals stay operator-side.
        shipping_carrier=order.shipping_carrier,
        shipping_tracking_number=order.shipping_tracking_number,
        shipping_tracking_url=order.shipping_tracking_url,
        discount_amount=float(order.discount_amount or 0.0),
        ship_to=ship_to,
        items=items,
        returns=returns,
        returnable=block_reason is None,
        return_window_days=window_days if window_days and window_days > 0 else 0,
        return_block_reason=block_reason,
    )


@router.get(
    "/me/orders/{order_id}",
    response_model=sales_order_schema.CustomerOrderDetail,
    tags=["customers"],
)
def read_my_order(
    order_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> "sales_order_schema.CustomerOrderDetail":
    """The authenticated customer's own order (detail + returns), cost-stripped.

    404 for any order the customer does not own (no existence oracle)."""
    order = _load_owned_order_or_404(db, order_id, current_user)
    return _customer_order_detail(db, order)


@router.post(
    "/me/orders/{order_id}/returns",
    response_model=sales_order_schema.CustomerOrderDetail,
    status_code=201,
    tags=["customers"],
)
def request_my_return(
    order_id: int,
    payload: sales_order_schema.CustomerReturnCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_customer),
) -> "sales_order_schema.CustomerOrderDetail":
    """Request a return on the customer's OWN order.

    Creates `requested` return row(s) — NO refund, NO stock movement (an
    operator approval drives those). The refund `amount` is derived server-side
    from the order's line prices; the client cannot dictate it. Idempotent on
    `idempotency_key`. Returns the refreshed order detail."""
    from src.services.sales_order_returns import (
        ReturnLineInput,
        request_return as svc_request_return,
    )

    order = _load_owned_order_or_404(db, order_id, current_user)
    lines = [
        ReturnLineInput(
            order_item_id=line.order_item_id,
            product_id=line.product_id,
            quantity=line.quantity,
        )
        for line in payload.lines
    ]
    svc_request_return(
        db,
        order=order,
        lines=lines,
        reason=payload.reason,
        requested_by=current_user,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    db.refresh(order)
    return _customer_order_detail(db, order)
