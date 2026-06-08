"""Schemas for the SAT/CFDI factura export (B7), export-only v1.

Emits realized sales in a CFDI 4.0-ready shape so an accountant or a PAC
(Facturama / SW Sapien) can timbrar them — typically as a *factura global
de público en general* for consumer marketplace sales. Full timbrado is
regulatory-heavy and intentionally deferred; this surface stops at the
structured export.

Per-buyer specific-RFC capture (needs SalesOrder columns + a capture UI)
is deferred — v1 issues every order to the RFC genérico
(`XAXX010101000`, "PÚBLICO EN GENERAL").
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class CfdiIssuerConfig(BaseModel):
    """The seller's own tax identity (the CFDI emisor)."""
    rfc: Optional[str] = None
    name: Optional[str] = None           # razón social
    tax_regime: Optional[str] = None     # clave régimen fiscal SAT (e.g. 601, 626)
    postal_code: Optional[str] = None    # lugar de expedición
    default_product_key: str = "01010101"  # ClaveProdServ fallback ("no existe")
    default_unit_key: str = "H87"          # ClaveUnidad (Pieza)
    cfdi_use: str = "S01"                  # uso CFDI (S01 = sin efectos fiscales)
    iva_rate: float = 0.16
    is_configured: bool = False
    # FP-06: per-channel "who issues the CFDI" policy. Keys are SalesOrder
    # source values (MERCADOLIBRE / AMAZON / FULCRUM); values are
    # 'self' (Fulcrum stamps via PAC) or 'marketplace_handled' (linked).
    invoicing_policy: Dict[str, str] = {}
    # PAC (stamping provider) status — the API key itself is never returned.
    pac_vendor: Optional[str] = None      # 'facturama' | 'finkok'
    pac_sandbox: bool = True
    pac_configured: bool = False


class CfdiIssuerConfigUpdate(BaseModel):
    rfc: Optional[str] = None
    name: Optional[str] = None
    tax_regime: Optional[str] = None
    postal_code: Optional[str] = None
    default_product_key: Optional[str] = None
    default_unit_key: Optional[str] = None
    cfdi_use: Optional[str] = None
    iva_rate: Optional[float] = None
    invoicing_policy: Optional[Dict[str, str]] = None
    pac_vendor: Optional[str] = None
    pac_sandbox: Optional[bool] = None
    pac_api_key: Optional[str] = None  # write-only; encrypted at rest


class CfdiDocumentOut(BaseModel):
    id: int
    order_id: Optional[int] = None
    kind: str
    status: str
    invoicing_source: str
    uuid: Optional[str] = None
    receiver_rfc: Optional[str] = None
    receiver_name: Optional[str] = None
    cfdi_use: Optional[str] = None
    currency: str
    subtotal_cents: int
    iva_cents: int
    total_cents: int
    pac_vendor: Optional[str] = None

    model_config = {"from_attributes": True}


class LinkExternalCfdiRequest(BaseModel):
    uuid: str
    receiver_rfc: Optional[str] = None
    receiver_name: Optional[str] = None


class NotaDeCreditoRequest(BaseModel):
    """Issue a nota de crédito (egreso) for a refund on an invoiced order."""

    amount_cents: int  # the refunded amount, in centavos
    idempotency_key: str  # a retry with the same key issues ONE credit note
    reason: Optional[str] = None


class NotaDeCreditoResponse(BaseModel):
    """Result of a nota-de-crédito request. ``issued`` is False when there is no
    invoice to credit (the caller treats that as a no-op skip, not an error)."""

    issued: bool
    status: str  # "stamped" | "no_ingreso" | "marketplace_handled"
    uuid: Optional[str] = None
    related_uuid: Optional[str] = None  # the original ingreso UUID
    amount_cents: int = 0


class CfdiConcept(BaseModel):
    description: str
    product_key: str   # ClaveProdServ
    unit_key: str      # ClaveUnidad
    quantity: int
    unit_price: float  # base (pre-IVA) unit price
    amount: float      # base (pre-IVA) line amount
    iva_amount: float


class CfdiOrderRow(BaseModel):
    order_id: int
    external_order_id: Optional[str] = None
    issued_at: datetime
    source: Optional[str] = None
    currency: str

    receiver_rfc: str
    receiver_name: str
    cfdi_use: str

    concepts: List[CfdiConcept]
    subtotal: float     # sum of base amounts
    iva_amount: float
    total: float        # tax-inclusive total


class CfdiReport(BaseModel):
    rows: List[CfdiOrderRow]
    issuer: CfdiIssuerConfig
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    order_count: int
    subtotal: float
    iva_amount: float
    total: float
