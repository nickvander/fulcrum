"""WhatsApp opt-out-by-phone (honor STOP) — service + endpoint coverage.

The storefront BFF forwards an inbound STOP here to clear a customer's
``whatsapp_opt_in``. Asserts:
  - matches across phone formats (+52.../52.../national 10-digit) on last-10,
  - opts out every matching customer; idempotent; unknown phone → 0,
  - only customers are affected (not admin/employee),
  - non-matching phones are untouched,
  - server-to-server X-API-Key auth required; no-auth rejected.
"""
from __future__ import annotations

import hashlib

import pytest
from sqlalchemy.orm import Session

from src.models.api_key import ApiKey
from src.models.user import User
from src.services.whatsapp_consent import normalize_phone, opt_out_by_phone


pytestmark = pytest.mark.db

_BASE = "/api/v1/customers/whatsapp-opt-out"
_SEED = {"n": 0}


def _make_customer(
    db: Session, *, phone: str | None, opt_in: bool = True, user_type: str = "customer"
) -> User:
    _SEED["n"] += 1
    user = User(
        email=f"wa{_SEED['n']}@example.com",
        hashed_password="x",
        user_type=user_type,
        is_active=True,
        phone=phone,
        whatsapp_opt_in=opt_in,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _api_key_headers(db: Session, user: User) -> dict[str, str]:
    raw_key = "bffwa-" + "f" * 58
    db.add(
        ApiKey(
            user_id=user.id,
            name="BFF whatsapp key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


# ---- normalize_phone ----


def test_normalize_phone_keeps_last_10_digits():
    assert normalize_phone("+52 55 1234 5678") == "5512345678"
    assert normalize_phone("5215512345678") == "5512345678"
    assert normalize_phone("5512345678") == "5512345678"
    assert normalize_phone("55-1234-5678") == "5512345678"


def test_normalize_phone_too_short_is_empty():
    assert normalize_phone("12345") == ""
    assert normalize_phone(None) == ""
    assert normalize_phone("") == ""


# ---- service: opt_out_by_phone ----


def test_opt_out_clears_consent_across_formats(db: Session):
    c = _make_customer(db, phone="+52 55 1234 5678")
    # Webhook delivers the wa_id like "5215512345678" (52 + 1 + national).
    updated = opt_out_by_phone(db, "5215512345678")
    assert updated == 1
    db.refresh(c)
    assert c.whatsapp_opt_in is False
    assert c.whatsapp_opt_in_at is not None


def test_opt_out_unknown_phone_returns_zero(db: Session):
    _make_customer(db, phone="5512345678")
    assert opt_out_by_phone(db, "5599999999") == 0


def test_opt_out_is_idempotent(db: Session):
    c = _make_customer(db, phone="5512345678")
    assert opt_out_by_phone(db, "5512345678") == 1
    # Already opted out → no longer a candidate → 0, stays opted out.
    assert opt_out_by_phone(db, "5512345678") == 0
    db.refresh(c)
    assert c.whatsapp_opt_in is False


def test_opt_out_only_affects_matching_customer(db: Session):
    target = _make_customer(db, phone="5512345678")
    other = _make_customer(db, phone="5598765432")
    assert opt_out_by_phone(db, "5512345678") == 1
    db.refresh(target)
    db.refresh(other)
    assert target.whatsapp_opt_in is False
    assert other.whatsapp_opt_in is True  # untouched


def test_opt_out_opts_out_all_matching_records(db: Session):
    a = _make_customer(db, phone="+525512345678")
    b = _make_customer(db, phone="5512345678")
    assert opt_out_by_phone(db, "5512345678") == 2
    db.refresh(a)
    db.refresh(b)
    assert a.whatsapp_opt_in is False
    assert b.whatsapp_opt_in is False


def test_opt_out_ignores_non_customers(db: Session):
    admin = _make_customer(db, phone="5512345678", user_type="admin")
    assert opt_out_by_phone(db, "5512345678") == 0
    db.refresh(admin)
    assert admin.whatsapp_opt_in is True  # admins aren't messaged / opted out here


def test_opt_out_too_short_phone_no_op(db: Session):
    _make_customer(db, phone="5512345678")
    assert opt_out_by_phone(db, "123") == 0


# ---- endpoint ----


def test_endpoint_opts_out_with_api_key(client, db: Session, test_admin_user):
    c = _make_customer(db, phone="5512345678")
    headers = _api_key_headers(db, test_admin_user)
    resp = client.post(_BASE, headers=headers, json={"phone": "5215512345678"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated"] == 1
    db.refresh(c)
    assert c.whatsapp_opt_in is False


def test_endpoint_unknown_phone_returns_zero(client, db: Session, test_admin_user):
    headers = _api_key_headers(db, test_admin_user)
    resp = client.post(_BASE, headers=headers, json={"phone": "5500000000"})
    assert resp.status_code == 200
    assert resp.json()["updated"] == 0


def test_endpoint_requires_auth(client):
    resp = client.post(_BASE, json={"phone": "5512345678"})
    assert resp.status_code in (401, 403)
