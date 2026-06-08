"""FP-11 hardening: API-key expiry enforcement, read-only scope, webhook token.

Exercises the security additions:
  * an expired API key is rejected (the column existed but was never enforced)
  * a read_only API key is blocked on write endpoints (require_write_scope),
    while a full key still writes
  * the MercadoLibre webhook requires the shared secret when configured, and is
    open (current behavior) when unset
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.config import settings
from src.models.api_key import ApiKey
from src.models.inventory import InventoryItem

pytestmark = pytest.mark.db

_ORDERS = f"{settings.API_V1_STR}/sales-orders/"
_ML_WEBHOOK = f"{settings.API_V1_STR}/webhooks/mercadolibre"


def _add_key(db: Session, user_id: int, *, raw: str, scope: str = "full", expires_at=None):
    db.add(
        ApiKey(
            user_id=user_id,
            name=f"key-{raw[:8]}",
            key_prefix=raw[:8],
            key_hash=hashlib.sha256(raw.encode()).hexdigest(),
            is_active=True,
            scope=scope,
            expires_at=expires_at,
        )
    )
    db.flush()


def _stock(db: Session, product, qty: int) -> None:
    db.add(InventoryItem(product_id=product.id, variant_id=None, quantity=qty, location="default"))
    db.flush()


def _order_payload(product, key: str) -> dict:
    return {"idempotency_key": key, "items": [{"product_id": product.id, "quantity": 1}]}


# ---- API key expiry --------------------------------------------------------- #


def test_expired_api_key_is_rejected(client: TestClient, db, test_product, test_admin_user):
    raw = "expired0-" + "a" * 55
    _add_key(
        db,
        test_admin_user.id,
        raw=raw,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    _stock(db, test_product, 5)
    resp = client.post(_ORDERS, headers={"X-API-Key": raw}, json=_order_payload(test_product, "exp"))
    assert resp.status_code == 401, resp.text
    assert "expired" in resp.json()["detail"].lower()


def test_unexpired_api_key_works(client: TestClient, db, test_product, test_admin_user):
    raw = "valid000-" + "b" * 55
    _add_key(
        db,
        test_admin_user.id,
        raw=raw,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    _stock(db, test_product, 5)
    resp = client.post(_ORDERS, headers={"X-API-Key": raw}, json=_order_payload(test_product, "ok"))
    assert resp.status_code == 201, resp.text


# ---- read-only scope -------------------------------------------------------- #


def test_read_only_key_blocked_on_write(client: TestClient, db, test_product, test_admin_user):
    raw = "readonly-" + "c" * 55
    _add_key(db, test_admin_user.id, raw=raw, scope="read_only")
    _stock(db, test_product, 5)
    resp = client.post(_ORDERS, headers={"X-API-Key": raw}, json=_order_payload(test_product, "ro"))
    assert resp.status_code == 403, resp.text
    assert "read-only" in resp.json()["detail"].lower()


def test_full_key_allows_write(client: TestClient, db, test_product, test_admin_user):
    raw = "fullkey0-" + "d" * 55
    _add_key(db, test_admin_user.id, raw=raw, scope="full")
    _stock(db, test_product, 5)
    resp = client.post(_ORDERS, headers={"X-API-Key": raw}, json=_order_payload(test_product, "full"))
    assert resp.status_code == 201, resp.text


# ---- api-key creation exposes scope ----------------------------------------- #


def test_create_api_key_endpoint_accepts_scope(client: TestClient, admin_headers):
    base = f"{settings.API_V1_STR}/integrations/api-keys"
    # Default scope is "full".
    full = client.post(base, headers=admin_headers, json={"name": "full key"})
    assert full.status_code == 200, full.text
    assert full.json()["scope"] == "full"
    # A read-only key can be minted explicitly.
    ro = client.post(base, headers=admin_headers, json={"name": "ro key", "scope": "read_only"})
    assert ro.status_code == 200, ro.text
    assert ro.json()["scope"] == "read_only"
    # An invalid scope is rejected by the schema.
    bad = client.post(base, headers=admin_headers, json={"name": "x", "scope": "wat"})
    assert bad.status_code == 422


# ---- inbound webhook shared secret ------------------------------------------ #


def test_ml_webhook_requires_token_when_configured(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "ML_WEBHOOK_VERIFY_TOKEN", "wh-secret", raising=False)
    body = {
        "resource": "/orders/1",
        "user_id": 1,
        "topic": "orders",
        "application_id": 1,
        "attempts": 1,
        "sent": "2026-06-08T00:00:00.000Z",
    }
    # No token → 401.
    assert client.post(_ML_WEBHOOK, json=body).status_code == 401
    # Wrong token → 401.
    assert client.post(_ML_WEBHOOK, json=body, headers={"X-Webhook-Token": "nope"}).status_code == 401
    # Correct token → accepted.
    ok = client.post(_ML_WEBHOOK, json=body, headers={"X-Webhook-Token": "wh-secret"})
    assert ok.status_code == 200, ok.text


def test_ml_webhook_open_when_token_unset(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "ML_WEBHOOK_VERIFY_TOKEN", None, raising=False)
    body = {
        "resource": "/orders/2",
        "user_id": 1,
        "topic": "orders",
        "application_id": 1,
        "attempts": 1,
        "sent": "2026-06-08T00:00:00.000Z",
    }
    assert client.post(_ML_WEBHOOK, json=body).status_code == 200
