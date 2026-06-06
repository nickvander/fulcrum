"""Schemas for the customer self-service (FP-05) endpoints.

These reuse the existing ``User`` and ``Address`` models. No new tables are
introduced; the magic-link flow reuses the ``password_reset_tokens`` table via
``crud.password_reset_token``.
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class CustomerRegister(BaseModel):
    """Payload for self-service customer registration."""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class CustomerProfile(BaseModel):
    """Safe customer profile (no hashed_password / admin-only fields)."""
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_opt_in: bool = False
    whatsapp_opt_in_at: Optional[str] = None
    user_type: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_orm(cls, obj):
        data = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if value is not None and isinstance(value, datetime):
                data[field_name] = value.isoformat()
            else:
                data[field_name] = value
        return cls(**data)

    model_config = ConfigDict(from_attributes=True)


class CustomerUpdate(BaseModel):
    """Fields a customer is allowed to update on their own profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    # WhatsApp transactional opt-in. Toggling this stamps ``whatsapp_opt_in_at``
    # server-side (the customer can't set the timestamp directly).
    whatsapp_opt_in: Optional[bool] = None


class WhatsAppOptOutRequest(BaseModel):
    """Server-to-server (BFF) opt-out by phone, triggered by an inbound STOP."""
    phone: str


class WhatsAppOptOutResult(BaseModel):
    """How many customer records had their WhatsApp consent cleared (no PII)."""
    updated: int


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerify(BaseModel):
    token: str


class MagicLinkToken(BaseModel):
    """Access token returned after a successful magic-link verification."""
    access_token: str
    token_type: str
