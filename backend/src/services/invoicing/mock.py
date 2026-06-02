"""Deterministic mock PAC for tests + local dev (FP-06 P1).

Produces a stable fake UUID/XML from the request so the stamp pipeline can
be exercised end-to-end without a real PAC. Selected automatically when no
PAC API key is configured (sandbox-less local runs) and in tests.
"""
from __future__ import annotations

import hashlib
from datetime import date

from .base import (
    CfdiStampRequest,
    CfdiStampResult,
    InvoicingError,
)


def _fake_uuid(req: CfdiStampRequest) -> str:
    """A UUID-shaped digest of the document so re-stamping identical input
    is deterministic (helps assert idempotency in tests)."""
    seed = f"{req.issuer_rfc}|{req.receiver_rfc}|{req.total_cents}|{req.external_ref}"
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}".upper()


class MockInvoicingProvider:
    vendor = "mock"

    def stamp(self, req: CfdiStampRequest) -> CfdiStampResult:
        if req.total_cents <= 0:
            raise InvoicingError("Mock PAC: non-positive total")
        uuid = _fake_uuid(req)
        xml = (
            f"<cfdi:Comprobante Total=\"{req.total_cents / 100:.2f}\" "
            f"Moneda=\"{req.currency}\"><TimbreFiscalDigital UUID=\"{uuid}\"/>"
            f"</cfdi:Comprobante>"
        )
        return CfdiStampResult(uuid=uuid, xml=xml, pdf_base64=None, pac_vendor=self.vendor)

    def cancel(self, uuid: str, reason: str) -> bool:
        return True

    def nota_de_credito(self, original_uuid: str, amount_cents: int) -> CfdiStampResult:
        raise InvoicingError("nota_de_credito not implemented in mock (P2)")

    def factura_global(self, start: date, end: date) -> CfdiStampResult:
        raise InvoicingError("factura_global not implemented in mock (P2)")
