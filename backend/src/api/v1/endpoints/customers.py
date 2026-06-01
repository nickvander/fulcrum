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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src import crud, models
from src.api import dependencies
from src.config import settings
from src.core import security
from src.core.errors import LocalizedHTTPException
from src.schemas import address as address_schema
from src.schemas import customer as customer_schema
from src.schemas.user import UserCreate, UserType

router = APIRouter()
logger = logging.getLogger(__name__)


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
def request_magic_link(
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
def verify_magic_link(
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

    Persists ``first_name`` / ``last_name`` / ``phone`` (the ``users.phone``
    column was added in migration ``a3f9c1d27b6e``).
    """
    update_data = customer_in.model_dump(exclude_unset=True)
    persistable = {
        k: v
        for k, v in update_data.items()
        if k in {"first_name", "last_name", "phone"}
    }
    for field, value in persistable.items():
        setattr(current_user, field, value)

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
