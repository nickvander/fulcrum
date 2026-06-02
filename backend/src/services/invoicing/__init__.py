"""CFDI invoicing providers (FP-06).

A single `InvoicingProvider` interface with concrete adapters. Fulcrum is
the only holder of the CSD private key + PAC API key (vendio forwards to
Fulcrum — see `work/future/96-fp06-cfdi-timbrado.md`).
"""
from .base import (
    CfdiStampRequest,
    CfdiStampResult,
    InvoicingError,
    InvoicingProvider,
)
from .mock import MockInvoicingProvider

__all__ = [
    "CfdiStampRequest",
    "CfdiStampResult",
    "InvoicingError",
    "InvoicingProvider",
    "MockInvoicingProvider",
]
