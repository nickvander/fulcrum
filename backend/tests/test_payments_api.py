"""
End-to-end tests for the payments API + the MercadoPago webhook
handler.

  - POST /api/v1/payments persists a Payment row + calls the
    connector + maps the provider status into the canonical
    PaymentStatus enum.
  - GET /api/v1/payments/{id} returns the row; 404 for unknown.
  - POST /api/v1/webhooks/mercadopago verifies the signature, then
    updates the matching Payment by external_payment_id.
  - Webhook idempotency: re-receiving the same notification doesn't
    duplicate the row, but DOES refresh status + last_webhook_payload.
  - Webhook unknown payment id: 200 from the endpoint (MP doesn't
    need a 4xx) but no row created.
  - Webhook bad signature: 401.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from src.api.v1.endpoints.webhooks import _process_mercadopago_event
from src.models.payment import Payment, PaymentStatus
from src.services.mercado_pago import PaymentResult


def _patched_session_local(db: Session):
    """Builds sessions bound to the test's connection so commits
    inside the background task join the fixture's outer transaction
    instead of opening a new one the test can't see. Same pattern the
    ML webhook tests use."""
    connection = db.connection()
    return sessionmaker(bind=connection, autocommit=False, autoflush=False)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# POST /api/v1/payments
# ---------------------------------------------------------------------------


def _payment_body(**overrides: Any) -> Dict[str, Any]:
    return {
        "token": "tok-abcd1234",
        "amount": 199.0,
        "currency": "MXN",
        "description": "Order 42",
        "payer_email": "alice@example.com",
        **overrides,
    }


def test_create_payment_persists_pending_then_applies_provider_result(
    client: TestClient, admin_headers: dict, db: Session,
):
    """Happy path: connector returns approved → Payment row stored
    with status=approved and the external id MP returned."""
    fake = PaymentResult(
        external_id="MP-PAY-9001",
        status="approved",
        raw={"id": "MP-PAY-9001", "status": "approved", "transaction_amount": 199.0},
    )
    with patch(
        "src.api.v1.endpoints.payments.mercado_pago_connector.create_payment",
        new=AsyncMock(return_value=fake),
    ) as mock_create:
        response = client.post(
            "/api/v1/payments/",
            json=_payment_body(),
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["external_payment_id"] == "MP-PAY-9001"
    assert body["status"] == PaymentStatus.APPROVED.value
    assert body["amount"] == 199.0
    assert body["currency"] == "MXN"
    # The connector was called with the body's token + amount; the
    # external_reference defaults to the internal payment id so the
    # webhook can link back.
    kwargs = mock_create.await_args.kwargs
    assert kwargs["token"] == "tok-abcd1234"
    assert kwargs["amount"] == 199.0
    assert kwargs["external_reference"] == str(body["id"])

    # Row really exists in the DB.
    row = db.query(Payment).filter(Payment.id == body["id"]).one()
    assert row.status == PaymentStatus.APPROVED.value
    assert row.external_payment_id == "MP-PAY-9001"


def test_create_payment_records_rejected_with_provider_error(
    client: TestClient, admin_headers: dict, db: Session,
):
    """MP rejects (bad token, insufficient funds, etc.) — we still
    persist the row but with status=rejected and the MP error
    captured into error_message so the UI can show it."""
    fake = PaymentResult(
        external_id=None,
        status="rejected",
        raw={"status": "rejected", "status_detail": "cc_rejected_insufficient_amount"},
        error="cc_rejected_insufficient_amount",
    )
    with patch(
        "src.api.v1.endpoints.payments.mercado_pago_connector.create_payment",
        new=AsyncMock(return_value=fake),
    ):
        response = client.post(
            "/api/v1/payments/",
            json=_payment_body(),
            headers=admin_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == PaymentStatus.REJECTED.value
    assert body["external_payment_id"] is None
    assert "cc_rejected" in (body["error_message"] or "")


def test_create_payment_via_stub_branch_with_no_mp_token_configured(
    client: TestClient, admin_headers: dict, db: Session,
):
    """When MERCADOPAGO_ACCESS_TOKEN is unset, the connector's stub
    branch fires — verifies the full endpoint→connector→DB path runs
    without mocking httpx at all."""
    with patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", None):
        response = client.post(
            "/api/v1/payments/",
            json=_payment_body(token="tok-stubpath"),
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == PaymentStatus.APPROVED.value
    assert body["external_payment_id"] == "STUB-MP-tok-stub"


def test_create_payment_via_stub_with_reject_token_lands_rejected(
    client: TestClient, admin_headers: dict, db: Session,
):
    with patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", None):
        response = client.post(
            "/api/v1/payments/",
            json=_payment_body(token="REJECT-test1"),
            headers=admin_headers,
        )
    body = response.json()
    assert body["status"] == PaymentStatus.REJECTED.value


# ---------------------------------------------------------------------------
# GET /api/v1/payments/{id}
# ---------------------------------------------------------------------------


def test_get_payment_returns_row(client: TestClient, admin_headers: dict, db: Session):
    p = Payment(amount=10.0, currency="MXN", status="approved", provider="mercado_pago")
    db.add(p)
    db.commit()
    db.refresh(p)

    response = client.get(f"/api/v1/payments/{p.id}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == p.id
    assert body["status"] == "approved"


def test_get_payment_404s_for_unknown_id(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/payments/999999", headers=admin_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/payments/  (list)
# ---------------------------------------------------------------------------


def _seed_payment(db: Session, **overrides: Any) -> Payment:
    base = dict(
        amount=10.0,
        currency="MXN",
        provider="mercado_pago",
        status=PaymentStatus.PENDING.value,
    )
    base.update(overrides)
    p = Payment(**base)
    db.add(p)
    db.flush()
    return p


def test_list_payments_returns_newest_first_with_total(
    client: TestClient, admin_headers: dict, db: Session,
):
    """Three payments inserted in order → list returns them id-desc
    and `total` matches the row count."""
    p1 = _seed_payment(db, amount=10.0, status=PaymentStatus.APPROVED.value)
    p2 = _seed_payment(db, amount=20.0, status=PaymentStatus.PENDING.value)
    p3 = _seed_payment(db, amount=30.0, status=PaymentStatus.REJECTED.value)
    db.commit()

    response = client.get("/api/v1/payments/", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    ids = [row["id"] for row in body["items"]]
    assert ids == [p3.id, p2.id, p1.id]


def test_list_payments_filters_by_status(
    client: TestClient, admin_headers: dict, db: Session,
):
    _seed_payment(db, status=PaymentStatus.APPROVED.value)
    _seed_payment(db, status=PaymentStatus.APPROVED.value)
    _seed_payment(db, status=PaymentStatus.REJECTED.value)
    db.commit()

    response = client.get(
        "/api/v1/payments/?status=approved", headers=admin_headers,
    )
    body = response.json()
    assert body["total"] == 2
    assert all(row["status"] == "approved" for row in body["items"])


def test_list_payments_filters_by_provider(
    client: TestClient, admin_headers: dict, db: Session,
):
    """The provider column is keyed for future Stripe / PayPal — filter
    works even though only one provider exists today."""
    _seed_payment(db, provider="mercado_pago")
    _seed_payment(db, provider="mercado_pago")
    _seed_payment(db, provider="stripe")
    db.commit()

    response = client.get(
        "/api/v1/payments/?provider=stripe", headers=admin_headers,
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["provider"] == "stripe"


def test_list_payments_paginates_with_skip_and_limit(
    client: TestClient, admin_headers: dict, db: Session,
):
    """Five payments + skip=2&limit=2 → returns items 3-4 (newest-first),
    but `total` is still 5 so the UI can render `3–4 of 5`."""
    ids = [_seed_payment(db, amount=float(i)).id for i in range(5)]
    db.commit()

    response = client.get(
        "/api/v1/payments/?skip=2&limit=2", headers=admin_headers,
    )
    body = response.json()
    assert body["total"] == 5
    page_ids = [row["id"] for row in body["items"]]
    # Newest-first → id desc → skip 2 = the 3rd + 4th-newest = ids[2], ids[1]
    assert page_ids == [ids[2], ids[1]]


def test_list_payments_requires_auth(client: TestClient):
    response = client.get("/api/v1/payments/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/webhooks/mercadopago
# ---------------------------------------------------------------------------


def _signed_header(secret: str, data_id: str, request_id: str, ts: str) -> str:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    sig = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={sig}"


def test_webhook_updates_existing_payment_status(db: Session):
    """Lifecycle: a pending Payment exists; MP webhook fires; we
    fetch the canonical status from MP and flip the row to approved.

    Drives _process_mercadopago_event directly (not via HTTP) because
    BackgroundTasks opens its own SessionLocal that can't see the
    test fixture's uncommitted transaction. The signature path is
    covered by the dedicated signature tests above.
    """
    p = Payment(
        amount=199.0, currency="MXN",
        status=PaymentStatus.PENDING.value,
        provider="mercado_pago",
        external_payment_id="MP-WEBHOOK-1",
    )
    db.add(p)
    db.commit()

    fetched = PaymentResult(
        external_id="MP-WEBHOOK-1",
        status="approved",
        raw={"id": "MP-WEBHOOK-1", "status": "approved"},
    )
    with (
        patch("src.api.v1.endpoints.webhooks.SessionLocal", new=_patched_session_local(db)),
        patch(
            "src.services.mercado_pago.mercado_pago_connector.fetch_payment",
            new=AsyncMock(return_value=fetched),
        ),
    ):
        asyncio.run(_process_mercadopago_event(
            {"type": "payment", "action": "payment.updated", "data": {"id": "MP-WEBHOOK-1"}},
        ))

    db.expire_all()
    refreshed = db.query(Payment).filter(Payment.id == p.id).one()
    assert refreshed.status == PaymentStatus.APPROVED.value
    assert refreshed.last_webhook_payload is not None


def test_webhook_idempotent_on_replay(db: Session):
    """Re-delivering the same notification refreshes the row's status
    + last_webhook_payload, but never creates a duplicate Payment.
    The unique (provider, external_payment_id) constraint is the
    final safety net."""
    p = Payment(
        amount=10.0, currency="MXN",
        status=PaymentStatus.PENDING.value,
        provider="mercado_pago",
        external_payment_id="MP-IDEMPO-1",
    )
    db.add(p)
    db.commit()

    fetched = PaymentResult(
        external_id="MP-IDEMPO-1", status="approved",
        raw={"id": "MP-IDEMPO-1", "status": "approved"},
    )
    with (
        patch("src.api.v1.endpoints.webhooks.SessionLocal", new=_patched_session_local(db)),
        patch(
            "src.services.mercado_pago.mercado_pago_connector.fetch_payment",
            new=AsyncMock(return_value=fetched),
        ),
    ):
        for _ in range(3):
            asyncio.run(_process_mercadopago_event(
                {"type": "payment", "data": {"id": "MP-IDEMPO-1"}},
            ))

    db.expire_all()
    rows = db.query(Payment).filter(Payment.external_payment_id == "MP-IDEMPO-1").all()
    assert len(rows) == 1
    assert rows[0].status == PaymentStatus.APPROVED.value


def test_webhook_for_unknown_payment_id_does_not_create_a_row(db: Session):
    """MP can deliver a webhook BEFORE the synchronous create-payment
    call returns (fast network + concurrent processing). The
    background task must ignore the notification rather than creating
    an orphan row."""
    fetched = PaymentResult(external_id="MP-GHOST", status="approved", raw={})
    with (
        patch("src.api.v1.endpoints.webhooks.SessionLocal", new=_patched_session_local(db)),
        patch(
            "src.services.mercado_pago.mercado_pago_connector.fetch_payment",
            new=AsyncMock(return_value=fetched),
        ),
    ):
        asyncio.run(_process_mercadopago_event(
            {"type": "payment", "data": {"id": "MP-GHOST"}},
        ))

    db.expire_all()
    assert db.query(Payment).filter(Payment.external_payment_id == "MP-GHOST").count() == 0


def test_webhook_rejects_invalid_signature(client: TestClient):
    """With a secret configured, an attacker without the secret
    cannot forge a valid x-signature → 401."""
    with patch("src.config.settings.MERCADOPAGO_WEBHOOK_SECRET", "whsec_test_secret"):
        response = client.post(
            "/api/v1/webhooks/mercadopago",
            json={"type": "payment", "data": {"id": "MP-EVIL"}},
            headers={"x-signature": "ts=1,v1=deadbeef"},
        )
    assert response.status_code == 401


def test_webhook_accepts_correctly_signed_notification(client: TestClient):
    """Round-trip: build a signature using the secret, post the
    webhook, get a 200. (DB update is covered by the background-task
    tests above — this test only asserts the signature-acceptance
    half of the endpoint.)"""
    secret = "whsec_round_trip"
    header = _signed_header(secret, data_id="MP-SIGN-OK", request_id="req-99", ts="1700000999")

    with patch("src.config.settings.MERCADOPAGO_WEBHOOK_SECRET", secret):
        response = client.post(
            "/api/v1/webhooks/mercadopago",
            json={"type": "payment", "data": {"id": "MP-SIGN-OK"}},
            headers={"x-signature": header, "x-request-id": "req-99"},
        )
    assert response.status_code == 200


def test_webhook_ignores_non_payment_event_types(client: TestClient, db: Session):
    """MP delivers many event types over the same URL — subscriptions,
    plans, chargebacks. Only `type=payment` is relevant to this
    handler; everything else returns 200 and does nothing."""
    with patch("src.config.settings.MERCADOPAGO_WEBHOOK_SECRET", None):
        with patch(
            "src.services.mercado_pago.mercado_pago_connector.fetch_payment",
            new=AsyncMock(),
        ) as mock_fetch:
            response = client.post(
                "/api/v1/webhooks/mercadopago",
                json={"type": "subscription", "data": {"id": "sub-1"}},
            )

    assert response.status_code == 200
    mock_fetch.assert_not_awaited()
