"""
Mercado Pago Checkout API connector.

Implements the server-side half of "Checkout Transparente" (Custom
Checkout): the frontend SDK tokenizes the card client-side and sends
the `token_id` + order metadata to our backend; we call MP's
`POST /v1/payments` with the token + amount to actually charge the
card; MP returns a payment id + status; we persist a `Payment` row
keyed by that id; subsequent `POST /webhooks/mercadopago` notifications
flip the status as it transitions (pending → approved / rejected /
refunded / chargeback / cancelled).

Signature verification on the webhook uses the `x-signature` header
documented at
https://www.mercadopago.com.ar/developers/en/docs/your-integrations/notifications/webhooks#signature.
The header looks like:
    ts=1234567890,v1=<hex>
and the manifest to HMAC is:
    id:<data.id>;request-id:<x-request-id>;ts:<ts>;
Verifying the signature is critical — MP webhooks carry NO user
authentication; the signature is the only proof the request came from
MP and not an attacker.

Stub branch: when `MERCADOPAGO_ACCESS_TOKEN` is unset, the connector
returns a deterministic stub response so dev/test paths can exercise
the full create-payment + webhook flow without live MP creds.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from src.config import settings


logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    """Normalized result of a create-payment call.

    `external_id`, `status`, and `raw` are always populated. `error`
    is set when MP rejected the request OR an exception was caught.
    The caller decides whether to surface `error` to the user.
    """
    external_id: Optional[str]
    status: str
    raw: Dict[str, Any]
    error: Optional[str] = None


class MercadoPagoConnector:
    """Thin wrapper around MP's REST API.

    Not subclassed from `BaseMarketplaceConnector` — MP is a payment
    gateway, not an inventory marketplace, so the interface is
    distinct (no listings / inventory / oauth flow).
    """

    @property
    def api_base_url(self) -> str:
        return settings.MERCADOPAGO_API_BASE_URL

    @property
    def is_configured(self) -> bool:
        """True when the server-side access token is set. False means
        the stub branch will activate on `create_payment`."""
        return bool(settings.MERCADOPAGO_ACCESS_TOKEN)

    async def create_payment(
        self,
        *,
        amount: float,
        token: str,
        description: str,
        payer_email: str,
        installments: int = 1,
        payment_method_id: Optional[str] = None,
        external_reference: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> PaymentResult:
        """Charge a card via MP's `POST /v1/payments`.

        - `token` is the `token_id` the frontend SDK produced after
          collecting card details — we never see raw PAN.
        - `idempotency_key` defaults to a random UUID per call. MP
          requires the `X-Idempotency-Key` header to dedupe retries;
          the caller can pass its own to make a retry deterministic.

        Returns a PaymentResult. Network / HTTP errors are caught and
        surfaced via `result.error` so the caller can persist the
        Payment row with an error_message rather than crashing.
        """
        if not self.is_configured:
            return _stub_create_payment(
                amount=amount, token=token, payer_email=payer_email,
                external_reference=external_reference,
            )

        url = f"{self.api_base_url}/v1/payments"
        headers = {
            "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
            "X-Idempotency-Key": idempotency_key or str(uuid.uuid4()),
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "transaction_amount": float(amount),
            "token": token,
            "description": description,
            "installments": installments,
            "payer": {"email": payer_email},
        }
        if payment_method_id:
            body["payment_method_id"] = payment_method_id
        if external_reference:
            body["external_reference"] = external_reference

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=body, timeout=30.0)
                data = _safe_json(response)
                if response.status_code >= 400:
                    # MP error responses contain `message` and
                    # sometimes `cause: [{description: ...}]`.
                    err = (data.get("message") if isinstance(data, dict) else None) or response.text
                    return PaymentResult(
                        external_id=str((data or {}).get("id")) if isinstance(data, dict) and data.get("id") else None,
                        status=str((data or {}).get("status", "rejected")),
                        raw=data if isinstance(data, dict) else {"text": response.text},
                        error=str(err)[:500],
                    )
                return PaymentResult(
                    external_id=str(data.get("id")) if data.get("id") is not None else None,
                    status=str(data.get("status") or "pending"),
                    raw=data,
                )
        except httpx.HTTPError as exc:
            logger.exception("Mercado Pago create_payment network error")
            return PaymentResult(
                external_id=None,
                status="rejected",
                raw={},
                error=f"network error: {exc}"[:500],
            )

    async def fetch_payment(self, external_id: str) -> PaymentResult:
        """`GET /v1/payments/{id}` — used by the webhook handler to
        get the canonical payment state (the webhook itself only
        carries the id, not the full payload)."""
        if not self.is_configured:
            return _stub_fetch_payment(external_id)

        url = f"{self.api_base_url}/v1/payments/{external_id}"
        headers = {"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=20.0)
                data = _safe_json(response)
                if response.status_code >= 400:
                    return PaymentResult(
                        external_id=external_id,
                        status="rejected",
                        raw=data if isinstance(data, dict) else {},
                        error=str((data or {}).get("message", response.text))[:500],
                    )
                return PaymentResult(
                    external_id=str(data.get("id") or external_id),
                    status=str(data.get("status") or "pending"),
                    raw=data,
                )
        except httpx.HTTPError as exc:
            logger.exception("Mercado Pago fetch_payment network error")
            return PaymentResult(
                external_id=external_id,
                status="pending",  # don't auto-flip to rejected on a transient
                raw={},
                error=f"network error: {exc}"[:500],
            )

    # ---- Webhook signature verification ----------------------------------

    @staticmethod
    def verify_webhook_signature(
        *,
        signature_header: Optional[str],
        request_id_header: Optional[str],
        data_id: Optional[str],
        secret: Optional[str],
    ) -> bool:
        """Verify the `x-signature` HMAC against the MP signing secret.

        Returns True on:
          - exact HMAC match, OR
          - no secret configured (dev / test mode — log a warning).
        Returns False on a mismatch.

        Doc reference (link in module docstring):
          manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
          expected = hmac_sha256(secret, manifest).hex()
          x-signature header: "ts=<ts>,v1=<expected>"
        """
        if not secret:
            logger.warning(
                "MercadoPago webhook signature check skipped — no secret "
                "configured. Set MERCADOPAGO_WEBHOOK_SECRET in production."
            )
            return True

        if not signature_header:
            return False

        # Parse "ts=...,v1=..." into a dict, tolerating extra whitespace.
        parts: Dict[str, str] = {}
        for kv in signature_header.split(","):
            if "=" not in kv:
                continue
            k, _, v = kv.partition("=")
            parts[k.strip()] = v.strip()
        ts = parts.get("ts")
        provided = parts.get("v1")
        if not ts or not provided:
            return False

        manifest = (
            f"id:{data_id or ''};"
            f"request-id:{request_id_header or ''};"
            f"ts:{ts};"
        )
        expected = hmac.new(
            secret.encode("utf-8"),
            manifest.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, provided)


mercado_pago_connector = MercadoPagoConnector()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        body = response.json()
        return body if isinstance(body, dict) else {"_body": body}
    except ValueError:
        return {}


def _stub_create_payment(
    *,
    amount: float,
    token: str,
    payer_email: str,
    external_reference: Optional[str],
) -> PaymentResult:
    """Deterministic stub response — used in dev / test environments
    where no MERCADOPAGO_ACCESS_TOKEN is set, and by the unit tests
    that exercise the create-payment endpoint without mocking httpx.

    A token starting with "REJECT-" returns rejected so callers can
    exercise the failure path without an MP sandbox."""
    if token.startswith("REJECT-"):
        return PaymentResult(
            external_id=f"STUB-MP-REJECT-{token[7:] or 'X'}",
            status="rejected",
            raw={
                "id": f"STUB-MP-REJECT-{token[7:] or 'X'}",
                "status": "rejected",
                "status_detail": "cc_rejected_other_reason",
                "transaction_amount": amount,
                "external_reference": external_reference,
            },
        )
    stub_id = f"STUB-MP-{token[:8] or 'TOKEN'}"
    return PaymentResult(
        external_id=stub_id,
        status="approved",
        raw={
            "id": stub_id,
            "status": "approved",
            "status_detail": "accredited",
            "transaction_amount": amount,
            "payer": {"email": payer_email},
            "external_reference": external_reference,
        },
    )


def _stub_fetch_payment(external_id: str) -> PaymentResult:
    """Mirror of `_stub_create_payment` for the fetch path."""
    if "REJECT" in external_id:
        return PaymentResult(
            external_id=external_id,
            status="rejected",
            raw={"id": external_id, "status": "rejected"},
        )
    return PaymentResult(
        external_id=external_id,
        status="approved",
        raw={"id": external_id, "status": "approved"},
    )
