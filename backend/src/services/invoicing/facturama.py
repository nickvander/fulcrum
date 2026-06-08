"""Facturama PAC adapter (FP-06, OD-04 default).

P1 implements `stamp` against Facturama's REST API. The payload shape
follows Facturama's CFDI 4.0 "Cfdi" model (JSON in → stamped XML/PDF +
UUID out), so we don't hand-author XML. The CSD is uploaded to Facturama
out-of-band (their CSD endpoint); this adapter only needs the API key.

NOTE [HIL]: the exact field names below must be confirmed against a live
Facturama **sandbox** before production use — verified end-to-end is a P1
acceptance gate. Tests use `MockInvoicingProvider`; this class is exercised
against the sandbox once credentials exist.
"""
from __future__ import annotations

import base64
from datetime import date

import httpx

from .base import (
    CfdiStampRequest,
    CfdiStampResult,
    InvoicingError,
)

_SANDBOX_BASE = "https://apisandbox.facturama.mx"
_PROD_BASE = "https://api.facturama.mx"


class FacturamaInvoicingProvider:
    vendor = "facturama"

    def __init__(self, api_key: str, *, sandbox: bool = True, timeout: float = 30.0):
        if not api_key:
            raise InvoicingError("Facturama API key not configured")
        self._base = _SANDBOX_BASE if sandbox else _PROD_BASE
        # Facturama uses HTTP Basic with the API key as username.
        token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
        self._headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        self._timeout = timeout

    def _payload(self, req: CfdiStampRequest) -> dict:
        return {
            "NameId": "1",  # 1 = factura (ingreso)
            "CfdiType": "I",
            "PaymentForm": "99",   # por definir — refine with checkout data later
            "PaymentMethod": "PUE",
            "Currency": req.currency,
            "ExpeditionPlace": req.issuer_postal_code,
            "Issuer": {
                "FiscalRegime": req.issuer_regime,
                "Rfc": req.issuer_rfc,
                "Name": req.issuer_name,
            },
            "Receiver": {
                "Rfc": req.receiver_rfc,
                "Name": req.receiver_name,
                "CfdiUse": req.cfdi_use,
                "FiscalRegime": req.receiver_regime or "616",
                "TaxZipCode": req.receiver_postal_code or req.issuer_postal_code,
            },
            "Items": [
                {
                    "ProductCode": c.product_key,
                    "UnitCode": c.unit_key,
                    "Description": c.description,
                    "Quantity": c.quantity,
                    "UnitPrice": round(c.unit_price_cents / 100, 2),
                    "Subtotal": round(c.amount_cents / 100, 2),
                    "TaxObject": "02",
                    "Taxes": [
                        {
                            "Total": round(c.iva_cents / 100, 2),
                            "Name": "IVA",
                            "Base": round(c.amount_cents / 100, 2),
                            "Rate": 0.16,
                            "IsRetention": False,
                        }
                    ],
                    "Total": round((c.amount_cents + c.iva_cents) / 100, 2),
                }
                for c in req.concepts
            ],
        }

    def stamp(self, req: CfdiStampRequest) -> CfdiStampResult:
        try:
            resp = httpx.post(
                f"{self._base}/3/cfdis",
                json=self._payload(req),
                headers=self._headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:  # network / timeout
            raise InvoicingError("Facturama request failed", retriable=True) from exc

        if resp.status_code >= 400:
            # Don't echo the response body verbatim — it can contain PII.
            raise InvoicingError(
                f"Facturama rejected the CFDI (HTTP {resp.status_code})",
                retriable=resp.status_code >= 500,
            )
        data = resp.json()
        uuid = data.get("Complement", {}).get("TaxStamp", {}).get("Uuid") or data.get("Id")
        if not uuid:
            raise InvoicingError("Facturama response missing UUID")
        return CfdiStampResult(
            uuid=uuid,
            xml=data.get("Xml", ""),
            pdf_base64=None,
            pac_vendor=self.vendor,
            raw={"id": data.get("Id")},
        )

    def cancel(self, uuid: str, reason: str) -> bool:
        raise InvoicingError("cancel not implemented (FP-06 P2)")

    def nota_de_credito(self, original_uuid: str, amount_cents: int) -> CfdiStampResult:
        """Issue an egreso (nota de crédito) related to ``original_uuid``.

        CFDI 4.0 egreso: ``CfdiType="E"`` with a ``Relations`` block of type
        ``01`` pointing at the original ingreso UUID, plus a single refund
        concept for the credited amount (IVA backed out at 16%).

        NOTE [HIL] TODO(live): confirm the exact Facturama egreso field names +
        the product/unit codes against the **sandbox** before production (same
        gate as ``stamp``). Also reconcile the 16% below with the issuer's
        configured ``iva_rate`` (the persisted egreso already uses it) so a
        non-default rate doesn't make the stamped split disagree with our books.
        Tests use the mock provider.
        """
        if amount_cents <= 0:
            raise InvoicingError("Non-positive credit-note amount")
        base_cents = round(amount_cents / 1.16)
        iva_cents = amount_cents - base_cents
        payload = {
            "NameId": "2",  # 2 = egreso (nota de crédito)
            "CfdiType": "E",
            "PaymentForm": "01",
            "PaymentMethod": "PUE",
            "Currency": "MXN",
            "Relations": {
                "Type": "01",  # nota de crédito de los documentos relacionados
                "Cfdis": [{"Uuid": original_uuid}],
            },
            "Items": [
                {
                    "ProductCode": "84111506",
                    "UnitCode": "ACT",
                    "Description": "Nota de crédito por devolución",
                    "Quantity": 1,
                    "UnitPrice": round(base_cents / 100, 2),
                    "Subtotal": round(base_cents / 100, 2),
                    "TaxObject": "02",
                    "Taxes": [
                        {
                            "Total": round(iva_cents / 100, 2),
                            "Name": "IVA",
                            "Base": round(base_cents / 100, 2),
                            "Rate": 0.16,
                            "IsRetention": False,
                        }
                    ],
                    "Total": round(amount_cents / 100, 2),
                }
            ],
        }
        try:
            resp = httpx.post(
                f"{self._base}/3/cfdis",
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise InvoicingError("Facturama request failed", retriable=True) from exc
        if resp.status_code >= 400:
            raise InvoicingError(
                f"Facturama rejected the nota de crédito (HTTP {resp.status_code})",
                retriable=resp.status_code >= 500,
            )
        data = resp.json()
        uuid = data.get("Complement", {}).get("TaxStamp", {}).get("Uuid") or data.get("Id")
        if not uuid:
            raise InvoicingError("Facturama response missing UUID")
        return CfdiStampResult(
            uuid=uuid,
            xml=data.get("Xml", ""),
            pdf_base64=None,
            pac_vendor=self.vendor,
            raw={"id": data.get("Id")},
        )

    def factura_global(self, start: date, end: date) -> CfdiStampResult:
        raise InvoicingError("factura_global not implemented (FP-06 P2)")
