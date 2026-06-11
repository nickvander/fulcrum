"""Discount codes (FP Phase 1) — validation engine + management API."""
import datetime

import pytest

from src.models.discount import DiscountCode  # noqa: F401  (ensures model import)
from src.services import discount_service

# DB-backed (real Postgres via the test harness); deselected from the fast,
# no-DB pre-commit subset like the other order/db tests.
pytestmark = pytest.mark.db


def _mk(db, **kw):
    defaults = dict(code="SAVE10", kind="percentage", value=10.0, is_active=True)
    defaults.update(kw)
    return discount_service.create_code(db, **defaults)


# ---- validation engine ----


def test_validate_percentage(db):
    _mk(db, code="SAVE10", kind="percentage", value=10.0)
    r = discount_service.validate_discount(db, "save10", 200.0)  # case-insensitive
    assert r.valid and r.discount_amount == 20.0 and r.kind == "percentage"


def test_validate_fixed_capped_at_subtotal(db):
    _mk(db, code="OFF50", kind="fixed", value=50.0)
    assert discount_service.validate_discount(db, "OFF50", 200.0).discount_amount == 50.0
    # fixed 50 off a 30 subtotal must cap at 30 (never a negative total)
    assert discount_service.validate_discount(db, "OFF50", 30.0).discount_amount == 30.0


def test_validate_not_found(db):
    r = discount_service.validate_discount(db, "NOPE", 100.0)
    assert not r.valid and r.reason == "not_found"


def test_validate_inactive(db):
    _mk(db, code="DEAD", value=10.0, is_active=False)
    r = discount_service.validate_discount(db, "DEAD", 100.0)
    assert not r.valid and r.reason == "inactive"


def test_validate_not_started_and_expired(db):
    now = datetime.datetime.now(datetime.timezone.utc)
    _mk(db, code="SOON", value=10.0, starts_at=now + datetime.timedelta(days=1))
    _mk(db, code="OLD", value=10.0, expires_at=now - datetime.timedelta(days=1))
    assert discount_service.validate_discount(db, "SOON", 100.0).reason == "not_started"
    assert discount_service.validate_discount(db, "OLD", 100.0).reason == "expired"


def test_validate_below_min_spend(db):
    _mk(db, code="BIG", value=10.0, min_spend=500.0)
    r = discount_service.validate_discount(db, "BIG", 100.0)
    assert not r.valid and r.reason == "below_min_spend"


def test_compute_rounds_to_two_dp(db):
    # 33% of 99.99 = 32.9967 -> 33.00
    assert discount_service.compute_discount_amount("percentage", 33.0, 99.99) == 33.00


# ---- management API ----


def test_validate_endpoint_is_public(client, db):
    _mk(db, code="PUB10", value=10.0)
    resp = client.post(
        "/api/v1/discount-codes/validate", json={"code": "pub10", "subtotal": 100.0}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is True and body["discount_amount"] == 10.0


def test_create_requires_write_scope(client):
    resp = client.post(
        "/api/v1/discount-codes",
        json={"code": "X1", "kind": "percentage", "value": 5},
    )
    assert resp.status_code in (401, 403)


def test_create_normalizes_and_rejects_duplicate(client, admin_headers):
    body = {"code": "newcode", "kind": "percentage", "value": 15}
    r1 = client.post("/api/v1/discount-codes", json=body, headers=admin_headers)
    assert r1.status_code == 201, r1.text
    assert r1.json()["code"] == "NEWCODE"  # stored normalized (uppercase)
    r2 = client.post("/api/v1/discount-codes", json=body, headers=admin_headers)
    assert r2.status_code == 409
