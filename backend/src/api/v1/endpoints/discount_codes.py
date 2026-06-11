"""Discount-code API (FP Phase 1). Mounted at `/api/v1/discount-codes`.

`POST /validate` is PUBLIC — the Vendio BFF calls it for the cart preview and it
records nothing. The CRUD routes require a write-scoped user / X-API-Key (codes
are managed in Fulcrum's ops surface, mirroring the category endpoints). The
discount is APPLIED + recorded at order-create (Phase 1b), never here.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api import dependencies
from src.api.dependencies import get_db
from src.models.discount import DiscountCode
from src.models.user import User
from src.schemas.discount import (
    DiscountCodeCreate,
    DiscountCodeOut,
    DiscountCodeUpdate,
    DiscountValidateRequest,
    DiscountValidationOut,
)
from src.services import discount_service

router = APIRouter()


@router.post("/validate", response_model=DiscountValidationOut)
def validate_code(
    payload: DiscountValidateRequest,
    db: Session = Depends(get_db),
) -> DiscountValidationOut:
    """PUBLIC cart-preview validation. Pure — records no redemption."""
    result = discount_service.validate_discount(
        db, payload.code, payload.subtotal, payload.customer_user_id
    )
    return DiscountValidationOut(
        valid=result.valid,
        reason=result.reason,
        kind=result.kind,
        value=result.value,
        discount_amount=result.discount_amount,
    )


@router.get("", response_model=List[DiscountCodeOut])
def list_discount_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
) -> List[DiscountCode]:
    return discount_service.list_codes(db)


@router.post("", response_model=DiscountCodeOut, status_code=201)
def create_discount_code(
    payload: DiscountCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
) -> DiscountCode:
    normalized = discount_service.normalize_code(payload.code)
    if db.query(DiscountCode).filter(DiscountCode.code == normalized).first() is not None:
        raise HTTPException(status_code=409, detail="A discount code with this code already exists.")
    return discount_service.create_code(db, **payload.model_dump())


@router.get("/{code_id}", response_model=DiscountCodeOut)
def get_discount_code(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
) -> DiscountCode:
    dc = discount_service.get_code(db, code_id)
    if dc is None:
        raise HTTPException(status_code=404, detail="Discount code not found.")
    return dc


@router.put("/{code_id}", response_model=DiscountCodeOut)
def update_discount_code(
    code_id: int,
    payload: DiscountCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
) -> DiscountCode:
    dc = discount_service.get_code(db, code_id)
    if dc is None:
        raise HTTPException(status_code=404, detail="Discount code not found.")
    fields = payload.model_dump(exclude_unset=True)
    if "code" in fields and fields["code"]:
        normalized = discount_service.normalize_code(fields["code"])
        clash = (
            db.query(DiscountCode)
            .filter(DiscountCode.code == normalized, DiscountCode.id != code_id)
            .first()
        )
        if clash is not None:
            raise HTTPException(status_code=409, detail="A discount code with this code already exists.")
    return discount_service.update_code(db, dc, **fields)


@router.delete("/{code_id}", status_code=204)
def delete_discount_code(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
) -> None:
    dc = discount_service.get_code(db, code_id)
    if dc is None:
        raise HTTPException(status_code=404, detail="Discount code not found.")
    discount_service.delete_code(db, dc)
