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
        """Egreso (credit note) linked to the original ingreso UUID (FP-06 P2).

        Deterministic: the same (original_uuid, amount) yields the same fake UUID
        so tests can assert idempotency, and it's distinct from the ingreso's UUID
        (seeded with an ``egreso`` tag)."""
        if amount_cents <= 0:
            raise InvoicingError("Mock PAC: non-positive credit-note amount")
        seed = f"egreso|{original_uuid}|{amount_cents}"
        h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
        uuid = f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}".upper()
        xml = (
            f'<cfdi:Comprobante TipoDeComprobante="E" '
            f'Total="{amount_cents / 100:.2f}">'
            f'<cfdi:CfdiRelacionados TipoRelacion="01">'
            f'<cfdi:CfdiRelacionado UUID="{original_uuid}"/>'
            f"</cfdi:CfdiRelacionados>"
            f'<TimbreFiscalDigital UUID="{uuid}"/></cfdi:Comprobante>'
        )
        return CfdiStampResult(uuid=uuid, xml=xml, pdf_base64=None, pac_vendor=self.vendor)

    def factura_global(self, start: date, end: date) -> CfdiStampResult:
        raise InvoicingError("factura_global not implemented in mock (P2)")
