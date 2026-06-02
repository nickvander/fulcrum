"""InvoicingProvider interface + value types (FP-06).

All amounts are **centavos** (integers) on the PAC path to avoid float
drift. RFC / fiscal data is PII — adapters must never log it raw.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class CfdiConceptInput:
    description: str
    product_key: str          # ClaveProdServ
    unit_key: str             # ClaveUnidad
    quantity: int
    unit_price_cents: int     # base (pre-IVA), centavos
    amount_cents: int         # base (pre-IVA) line total, centavos
    iva_cents: int


@dataclass(frozen=True)
class CfdiStampRequest:
    # Emisor
    issuer_rfc: str
    issuer_name: str
    issuer_regime: str
    issuer_postal_code: str
    # Receptor
    receiver_rfc: str
    receiver_name: str
    receiver_postal_code: Optional[str]
    receiver_regime: Optional[str]
    cfdi_use: str
    # Document
    concepts: List[CfdiConceptInput]
    subtotal_cents: int
    iva_cents: int
    total_cents: int
    currency: str = "MXN"
    series: Optional[str] = None
    external_ref: Optional[str] = None  # e.g. order id, for traceability


@dataclass(frozen=True)
class CfdiStampResult:
    uuid: str                 # folio fiscal returned by the PAC
    xml: str                  # stamped XML
    pdf_base64: Optional[str] = None
    pac_vendor: str = ""
    raw: dict = field(default_factory=dict)


class InvoicingError(Exception):
    """A PAC rejected the request or the call failed. Carries a safe,
    non-PII message for surfacing to the operator."""

    def __init__(self, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.retriable = retriable


@runtime_checkable
class InvoicingProvider(Protocol):
    """A certified PAC adapter. P1 implements `stamp`; cancel / nota de
    crédito / factura global land in P2 (kept on the interface so the
    contract is stable)."""

    vendor: str

    def stamp(self, req: CfdiStampRequest) -> CfdiStampResult: ...

    def cancel(self, uuid: str, reason: str) -> bool: ...

    def nota_de_credito(self, original_uuid: str, amount_cents: int) -> CfdiStampResult: ...

    def factura_global(self, start: date, end: date) -> CfdiStampResult: ...
