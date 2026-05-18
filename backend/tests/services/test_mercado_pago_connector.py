"""
Coverage for `services/mercado_pago.py`:
  - Stub branch (no MERCADOPAGO_ACCESS_TOKEN configured) for both
    create_payment and fetch_payment, including the REJECT- token
    convention.
  - Real-HTTP branch: correct URL, headers (Bearer + idempotency
    key), body shape, status_code mapping (200, 4xx).
  - PaymentStatus.from_mercado_pago coverage of every MP status the
    docs publish, including the unknown-fallback to PENDING.
  - HMAC signature verification: matching, mismatching, missing
    header, missing secret (skip-with-warning branch).
"""
from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.models.payment import PaymentStatus
from src.services.mercado_pago import MercadoPagoConnector, _stub_create_payment


# ---------------------------------------------------------------------------
# PaymentStatus.from_mercado_pago
# ---------------------------------------------------------------------------


def test_payment_status_from_mercado_pago_maps_all_documented_statuses():
    assert PaymentStatus.from_mercado_pago("approved") == PaymentStatus.APPROVED
    assert PaymentStatus.from_mercado_pago("rejected") == PaymentStatus.REJECTED
    assert PaymentStatus.from_mercado_pago("cancelled") == PaymentStatus.CANCELLED
    # All three "money came back" statuses collapse to REFUNDED so the
    # caller has one bucket for "the customer doesn't owe us anymore".
    for refund_state in ("refunded", "charged_back", "partially_refunded"):
        assert PaymentStatus.from_mercado_pago(refund_state) == PaymentStatus.REFUNDED
    # Pending family — also collapses to PENDING.
    for pending_state in ("pending", "in_process", "authorized", "in_mediation"):
        assert PaymentStatus.from_mercado_pago(pending_state) == PaymentStatus.PENDING
    # Unknown status / empty / None — default to PENDING (safer than
    # auto-flipping to REJECTED on a typo).
    assert PaymentStatus.from_mercado_pago("future_unknown_status") == PaymentStatus.PENDING
    assert PaymentStatus.from_mercado_pago("") == PaymentStatus.PENDING


# ---------------------------------------------------------------------------
# create_payment — stub branch
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_payment_returns_stub_when_access_token_unset():
    """No MERCADOPAGO_ACCESS_TOKEN → stub branch. No HTTP call, but
    we still get a deterministic external_id + status the caller can
    persist."""
    connector = MercadoPagoConnector()
    with patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", None):
        with patch("httpx.AsyncClient.post") as mock_post:
            result = await connector.create_payment(
                amount=199.00, token="tok-abcdefgh", description="x",
                payer_email="alice@example.com",
            )
    mock_post.assert_not_called()
    assert result.error is None
    assert result.status == "approved"
    assert result.external_id == "STUB-MP-tok-abcd"
    assert result.raw["transaction_amount"] == 199.00


@pytest.mark.anyio
async def test_create_payment_stub_rejects_for_reject_prefixed_token():
    """REJECT- token convention so failure-path tests don't need an
    MP sandbox."""
    connector = MercadoPagoConnector()
    with patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", None):
        result = await connector.create_payment(
            amount=10.00, token="REJECT-fake", description="x",
            payer_email="alice@example.com",
        )
    assert result.status == "rejected"
    assert result.external_id == "STUB-MP-REJECT-fake"


# ---------------------------------------------------------------------------
# create_payment — real-HTTP branch
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_payment_posts_to_mp_with_bearer_and_idempotency_headers():
    connector = MercadoPagoConnector()
    mp_response = {"id": 88001122, "status": "approved", "transaction_amount": 199.0}

    with (
        patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", "TEST-MP-TOKEN"),
        patch("src.config.settings.MERCADOPAGO_API_BASE_URL", "https://api.mercadopago.com"),
        patch("httpx.AsyncClient.post") as mock_post,
    ):
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mp_response,
            text="",
        )
        result = await connector.create_payment(
            amount=199.0, token="tok-abc", description="Test",
            payer_email="alice@example.com",
            installments=3, payment_method_id="visa",
            external_reference="42",
            idempotency_key="fixed-key",
        )

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.mercadopago.com/v1/payments"
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer TEST-MP-TOKEN"
    assert headers["X-Idempotency-Key"] == "fixed-key"
    body = kwargs["json"]
    assert body["transaction_amount"] == 199.0
    assert body["token"] == "tok-abc"
    assert body["installments"] == 3
    assert body["payer"] == {"email": "alice@example.com"}
    assert body["payment_method_id"] == "visa"
    assert body["external_reference"] == "42"

    # Result correctly normalized.
    assert result.external_id == "88001122"
    assert result.status == "approved"
    assert result.error is None


@pytest.mark.anyio
async def test_create_payment_surfaces_mp_error_responses_via_result_error():
    """A 4xx from MP must NOT raise — we capture the message into
    `result.error` so the caller can persist the Payment row with an
    error_message instead of losing the failure entirely."""
    connector = MercadoPagoConnector()
    mp_error = {"message": "Invalid card token", "cause": [{"code": 2034}], "status": "rejected"}

    with (
        patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", "TEST-MP-TOKEN"),
        patch("httpx.AsyncClient.post") as mock_post,
    ):
        mock_post.return_value = AsyncMock(
            status_code=400,
            json=lambda: mp_error,
            text="bad",
        )
        result = await connector.create_payment(
            amount=10.0, token="tok-x", description="x",
            payer_email="alice@example.com",
        )

    assert result.error == "Invalid card token"
    assert result.status == "rejected"


@pytest.mark.anyio
async def test_create_payment_catches_network_errors_and_returns_rejected():
    """httpx.HTTPError on a network failure must not crash the endpoint.
    Caller can decide whether to retry based on `result.error`."""
    connector = MercadoPagoConnector()

    with (
        patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", "TEST-MP-TOKEN"),
        patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("DNS fail")),
    ):
        result = await connector.create_payment(
            amount=10.0, token="tok-x", description="x",
            payer_email="alice@example.com",
        )

    assert result.external_id is None
    assert result.status == "rejected"
    assert "network error" in (result.error or "")


# ---------------------------------------------------------------------------
# fetch_payment
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_payment_calls_mp_get_with_bearer():
    connector = MercadoPagoConnector()
    with (
        patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", "TEST-MP-TOKEN"),
        patch("src.config.settings.MERCADOPAGO_API_BASE_URL", "https://api.mercadopago.com"),
        patch("httpx.AsyncClient.get") as mock_get,
    ):
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"id": 999, "status": "approved"},
            text="",
        )
        result = await connector.fetch_payment("999")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://api.mercadopago.com/v1/payments/999"
    assert kwargs["headers"]["Authorization"] == "Bearer TEST-MP-TOKEN"
    assert result.external_id == "999"
    assert result.status == "approved"


@pytest.mark.anyio
async def test_fetch_payment_stays_pending_on_transient_network_error():
    """A network error on fetch must NOT flip the status to rejected
    — the webhook handler would otherwise overwrite a healthy
    Payment.status with a fake rejection just because MP was slow."""
    connector = MercadoPagoConnector()
    with (
        patch("src.config.settings.MERCADOPAGO_ACCESS_TOKEN", "TEST-MP-TOKEN"),
        patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("DNS fail")),
    ):
        result = await connector.fetch_payment("999")
    assert result.status == "pending"


# ---------------------------------------------------------------------------
# verify_webhook_signature
# ---------------------------------------------------------------------------


def _signed_header(secret: str, data_id: str, request_id: str, ts: str) -> str:
    """Build a valid `x-signature` header value the way MP would."""
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    sig = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={sig}"


def test_signature_verification_accepts_matching_hmac():
    secret = "whsec_test_123"
    header = _signed_header(secret, data_id="payment-42", request_id="req-1", ts="1700000000")
    assert MercadoPagoConnector.verify_webhook_signature(
        signature_header=header,
        request_id_header="req-1",
        data_id="payment-42",
        secret=secret,
    ) is True


def test_signature_verification_rejects_tampered_hmac():
    secret = "whsec_test_123"
    header = _signed_header(secret, data_id="payment-42", request_id="req-1", ts="1700000000")
    # Replace one hex char in the v1 value.
    tampered = header[:-1] + ("0" if header[-1] != "0" else "1")
    assert MercadoPagoConnector.verify_webhook_signature(
        signature_header=tampered,
        request_id_header="req-1",
        data_id="payment-42",
        secret=secret,
    ) is False


def test_signature_verification_rejects_wrong_data_id():
    """Replay protection: an attacker that captured a valid x-signature
    for payment 42 can't replay it for payment 43 — the manifest
    includes the data id."""
    secret = "whsec_test_123"
    header = _signed_header(secret, data_id="payment-42", request_id="req-1", ts="1700000000")
    assert MercadoPagoConnector.verify_webhook_signature(
        signature_header=header,
        request_id_header="req-1",
        data_id="payment-43",  # different
        secret=secret,
    ) is False


def test_signature_verification_rejects_missing_header():
    assert MercadoPagoConnector.verify_webhook_signature(
        signature_header=None,
        request_id_header="req-1",
        data_id="payment-42",
        secret="whsec_test_123",
    ) is False


def test_signature_verification_skips_when_no_secret_configured():
    """Dev/test convenience: an unset secret means "accept and log",
    so a local dev workspace can post webhooks without configuring a
    signing key. Production MUST set the secret."""
    assert MercadoPagoConnector.verify_webhook_signature(
        signature_header="ts=123,v1=abc",
        request_id_header="req-1",
        data_id="payment-42",
        secret=None,
    ) is True


# ---------------------------------------------------------------------------
# Stub helper directly
# ---------------------------------------------------------------------------


def test_stub_create_payment_preserves_external_reference_in_raw():
    """The frontend SDK flow sets `external_reference` to the Fulcrum
    payment id; the stub must keep it round-tripped so the webhook
    handler that reads it doesn't break in tests."""
    result = _stub_create_payment(
        amount=49.99, token="tok-xyz", payer_email="x@y.z",
        external_reference="123",
    )
    assert result.raw["external_reference"] == "123"
