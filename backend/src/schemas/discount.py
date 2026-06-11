"""Discount-code DTOs (FP Phase 1). Money is Float pesos."""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DiscountValidateRequest(BaseModel):
    """Cart-preview validation (the BFF calls this; records nothing)."""

    code: str = Field(..., min_length=1, max_length=64)
    subtotal: float = Field(..., ge=0, description="Eligible subtotal in Float pesos.")
    customer_user_id: Optional[int] = Field(default=None, gt=0)


class DiscountValidationOut(BaseModel):
    valid: bool
    # One of the discount_service REASON_* codes when invalid; None when valid.
    reason: Optional[str] = None
    kind: Optional[str] = None
    value: Optional[float] = None
    discount_amount: float = 0.0


class DiscountCodeBase(BaseModel):
    description: Optional[str] = Field(default=None, max_length=255)
    kind: str = Field(default="percentage", pattern=r"^(percentage|fixed)$")
    value: float = Field(..., ge=0)
    min_spend: Optional[float] = Field(default=None, ge=0)
    starts_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
    is_active: bool = True
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    per_customer_limit: Optional[int] = Field(default=None, ge=1)


class DiscountCodeCreate(DiscountCodeBase):
    code: str = Field(..., min_length=1, max_length=64)


class DiscountCodeUpdate(BaseModel):
    """All optional — only sent fields are changed."""

    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=255)
    kind: Optional[str] = Field(default=None, pattern=r"^(percentage|fixed)$")
    value: Optional[float] = Field(default=None, ge=0)
    min_spend: Optional[float] = Field(default=None, ge=0)
    starts_at: Optional[datetime.datetime] = None
    expires_at: Optional[datetime.datetime] = None
    is_active: Optional[bool] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    per_customer_limit: Optional[int] = Field(default=None, ge=1)


class DiscountCodeOut(DiscountCodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
