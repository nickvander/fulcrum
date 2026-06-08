"""CFDI live stamping (FP-06 P1).

Turns a single realized order into a stamped CFDI via an
`InvoicingProvider`, honoring the per-channel invoicing policy so a
marketplace that issues its own facturas (e.g. MercadoLibre) is never
double-invoiced — those orders are *linked* (their UUID recorded) instead.

Reuses B7's per-line IVA back-out (`cfdi_service._backout_iva`) so the
export and the stamp agree on the numbers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.cfdi_document import CfdiDocument
from src.models.order import SalesOrder, SalesOrderItem
from src.models.product import Product
from src.services import cfdi_service
from src.services.invoicing import (
    CfdiStampRequest,
    InvoicingError,
    InvoicingProvider,
    MockInvoicingProvider,
)
from src.services.invoicing.base import CfdiConceptInput

logger = logging.getLogger(__name__)


def _cents(pesos: float) -> int:
    return int(round(pesos * 100))


def resolve_invoicing_source(db: Session, order_source: Optional[str]) -> str:
    """'self' or 'marketplace_handled' for a given SalesOrder.source."""
    policy = cfdi_service.read_issuer_config(db).invoicing_policy
    return policy.get((order_source or "").upper(), "self")


def get_provider(db: Session) -> InvoicingProvider:
    """Live PAC adapter when a key is configured, else the deterministic
    mock (local/sandbox-less runs + tests)."""
    key = cfdi_service.resolve_pac_api_key(db)
    if not key:
        return MockInvoicingProvider()
    issuer = cfdi_service.read_issuer_config(db)
    if (issuer.pac_vendor or "facturama").lower() == "facturama":
        from src.services.invoicing.facturama import FacturamaInvoicingProvider

        return FacturamaInvoicingProvider(key, sandbox=issuer.pac_sandbox)
    # Finkok etc. land behind the same interface in a later phase.
    return MockInvoicingProvider()


def build_stamp_request(db: Session, order: SalesOrder, issuer) -> CfdiStampRequest:
    iva_rate = issuer.iva_rate
    item_rows = (
        db.query(SalesOrderItem, Product.name)
        .outerjoin(Product, Product.id == SalesOrderItem.product_id)
        .filter(SalesOrderItem.order_id == order.id)
        .all()
    )
    concepts: list[CfdiConceptInput] = []
    sub = iva = 0.0
    for item, product_name in item_rows:
        qty = int(item.quantity or 0)
        unit_inc = float(item.price_per_unit or 0.0)
        line_inc = unit_inc * qty
        base, line_iva = cfdi_service._backout_iva(line_inc, iva_rate)
        unit_base, _ = cfdi_service._backout_iva(unit_inc, iva_rate)
        concepts.append(
            CfdiConceptInput(
                description=product_name or f"Producto {item.product_id}",
                product_key=issuer.default_product_key,
                unit_key=issuer.default_unit_key,
                quantity=qty,
                unit_price_cents=_cents(unit_base),
                amount_cents=_cents(base),
                iva_cents=_cents(line_iva),
            )
        )
        sub += base
        iva += line_iva

    subtotal_cents = _cents(round(sub, 2))
    iva_cents = _cents(round(iva, 2))
    total_cents = subtotal_cents + iva_cents  # CFDI: Total = SubTotal + taxes

    # Specific receiver when captured at checkout, else público en general.
    if order.cfdi_receiver_rfc:
        receiver_rfc = order.cfdi_receiver_rfc
        receiver_name = order.cfdi_receiver_name or ""
    else:
        receiver_rfc = cfdi_service.RFC_GENERICO
        receiver_name = cfdi_service.RECEIVER_PUBLICO_GENERAL

    return CfdiStampRequest(
        issuer_rfc=issuer.rfc or "",
        issuer_name=issuer.name or "",
        issuer_regime=issuer.tax_regime or "",
        issuer_postal_code=issuer.postal_code or "",
        receiver_rfc=receiver_rfc,
        receiver_name=receiver_name,
        receiver_postal_code=order.cfdi_receiver_postal_code,
        receiver_regime=order.cfdi_receiver_regime,
        cfdi_use=order.cfdi_use or issuer.cfdi_use,
        concepts=concepts,
        subtotal_cents=subtotal_cents,
        iva_cents=iva_cents,
        total_cents=total_cents,
        currency=order.currency or "MXN",
        external_ref=str(order.id),
    )


def _by_idempotency_key(db: Session, key: str) -> Optional[CfdiDocument]:
    return (
        db.query(CfdiDocument).filter(CfdiDocument.idempotency_key == key).first()
    )


def _existing_stamped(db: Session, order_id: int) -> Optional[CfdiDocument]:
    return (
        db.query(CfdiDocument)
        .filter(CfdiDocument.order_id == order_id)
        .filter(CfdiDocument.kind == "ingreso")
        .filter(CfdiDocument.status == "stamped")
        .first()
    )


def stamp_order(
    db: Session,
    order_id: int,
    *,
    provider: Optional[InvoicingProvider] = None,
) -> Dict[str, Any]:
    """Stamp one order's CFDI via the PAC.

      - unknown order                 -> {"error": "not_found"}
      - channel issues its own CFDI   -> {"error": "marketplace_handled"}
      - emisor not configured         -> {"error": "issuer_not_configured"}
      - PAC rejected / failed         -> {"error": "stamp_failed", "detail": ...}
    Idempotent: an already-stamped order returns the existing document.
    On success returns {"document": <CfdiDocument>}.
    """
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if order is None:
        return {"error": "not_found"}

    if resolve_invoicing_source(db, order.source) == "marketplace_handled":
        # e.g. MercadoLibre stamps these — record via link_external, not here.
        return {"error": "marketplace_handled"}

    existing = _existing_stamped(db, order_id)
    if existing is not None:
        return {"document": existing}

    issuer = cfdi_service.read_issuer_config(db)
    if not issuer.is_configured:
        return {"error": "issuer_not_configured"}

    req = build_stamp_request(db, order, issuer)
    if req.total_cents <= 0:
        return {"error": "empty_order"}

    provider = provider or get_provider(db)
    try:
        result = provider.stamp(req)
    except InvoicingError as exc:
        logger.warning("CFDI stamp failed for order %d: %s", order_id, exc)
        return {"error": "stamp_failed", "detail": str(exc)}

    doc = CfdiDocument(
        order_id=order.id,
        kind="ingreso",
        status="stamped",
        invoicing_source="self",
        uuid=result.uuid,
        receiver_rfc=req.receiver_rfc,
        receiver_name=req.receiver_name,
        receiver_postal_code=req.receiver_postal_code,
        receiver_regime=req.receiver_regime,
        cfdi_use=req.cfdi_use,
        currency=req.currency,
        subtotal_cents=req.subtotal_cents,
        iva_cents=req.iva_cents,
        total_cents=req.total_cents,
        pac_vendor=result.pac_vendor,
        xml_path=_persist_xml(result.uuid, result.xml),
        stamped_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document": doc}


def link_external(
    db: Session,
    order_id: int,
    uuid: str,
    *,
    receiver_rfc: Optional[str] = None,
    receiver_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a CFDI issued elsewhere (e.g. MercadoLibre's automatic
    facturación) so the books stay complete without double-issuing.
    Idempotent on the UUID."""
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if order is None:
        return {"error": "not_found"}
    if not (uuid or "").strip():
        return {"error": "missing_uuid"}

    existing = db.query(CfdiDocument).filter(CfdiDocument.uuid == uuid).first()
    if existing is not None:
        return {"document": existing}

    doc = CfdiDocument(
        order_id=order.id,
        kind="ingreso",
        status="stamped",
        invoicing_source="marketplace_handled",
        uuid=uuid,
        receiver_rfc=receiver_rfc,
        receiver_name=receiver_name,
        currency=order.currency or "MXN",
        stamped_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"document": doc}


def issue_nota_de_credito(
    db: Session,
    order_id: int,
    amount_cents: int,
    idempotency_key: str,
    *,
    reason: Optional[str] = None,
    provider: Optional[InvoicingProvider] = None,
) -> Dict[str, Any]:
    """Issue an egreso (nota de crédito) for a refund on an invoiced order.

      - already issued for this key   -> {"document": <existing egreso>} (idempotent)
      - order has no stamped ingreso  -> {"error": "no_ingreso"}
      - the ingreso was issued elsewhere (marketplace) -> {"error": "marketplace_handled"}
      - amount <= 0                   -> {"error": "invalid_amount"}
      - amount + prior egresos > invoice total -> {"error": "amount_exceeds_invoice"}
      - PAC rejected                  -> {"error": "stamp_failed", "detail": ...}
    On success returns {"document": <new egreso CfdiDocument>}. Amounts are
    centavos. ``idempotency_key`` makes a refund retry produce ONE credit note.
    """
    if not (idempotency_key or "").strip():
        return {"error": "missing_idempotency_key"}

    # Fast idempotent path (no lock) — a completed credit note replays instantly.
    existing = _by_idempotency_key(db, idempotency_key)
    if existing is not None:
        return {"document": existing}

    if amount_cents <= 0:
        return {"error": "invalid_amount"}

    # Lock the ingreso row FOR UPDATE so all credit-notes for this order
    # SERIALIZE: the cap (read sum → insert) is otherwise a race where two
    # concurrent refunds with different keys both read the same `already_credited`
    # and over-credit the invoice. The lock also serializes same-key races so the
    # re-check below resolves them idempotently instead of double-stamping.
    ingreso = (
        db.query(CfdiDocument)
        .filter(CfdiDocument.order_id == order_id)
        .filter(CfdiDocument.kind == "ingreso")
        .filter(CfdiDocument.status == "stamped")
        .with_for_update()
        .first()
    )
    if ingreso is None:
        return {"error": "no_ingreso"}
    if (ingreso.invoicing_source or "self") != "self":
        # The marketplace that stamped the ingreso also handles its credit notes.
        return {"error": "marketplace_handled"}

    # Re-check idempotency INSIDE the lock: a concurrent same-key request that
    # committed while we waited for the lock is now visible.
    existing = _by_idempotency_key(db, idempotency_key)
    if existing is not None:
        return {"document": existing}

    # Cap: the sum of credit notes must not exceed the original invoice total.
    already_credited = int(
        db.query(func.coalesce(func.sum(CfdiDocument.total_cents), 0))
        .filter(CfdiDocument.order_id == order_id)
        .filter(CfdiDocument.kind == "egreso")
        .filter(CfdiDocument.status == "stamped")
        .scalar()
        or 0
    )
    creditable = int(ingreso.total_cents) - already_credited
    if amount_cents > creditable:
        return {"error": "amount_exceeds_invoice", "creditable_cents": creditable}

    provider = provider or get_provider(db)
    try:
        result = provider.nota_de_credito(ingreso.uuid, amount_cents)
    except InvoicingError as exc:
        logger.warning("nota de credito failed for order %d: %s", order_id, exc)
        return {"error": "stamp_failed", "detail": str(exc)}

    # Split the credited total on the SAME basis as the original invoice — use
    # the issuer's configured IVA rate (not a hardcoded 16%) so the egreso's tax
    # split is consistent with the ingreso. IVA is the residual so the parts sum
    # back to the total exactly.
    iva_rate = cfdi_service.read_issuer_config(db).iva_rate
    base_pesos, _ = cfdi_service._backout_iva(amount_cents / 100, iva_rate)
    subtotal_cents = _cents(base_pesos)
    doc = CfdiDocument(
        order_id=order_id,
        kind="egreso",
        status="stamped",
        invoicing_source="self",
        uuid=result.uuid,
        related_uuid=ingreso.uuid,
        idempotency_key=idempotency_key,
        receiver_rfc=ingreso.receiver_rfc,
        receiver_name=ingreso.receiver_name,
        receiver_postal_code=ingreso.receiver_postal_code,
        receiver_regime=ingreso.receiver_regime,
        cfdi_use=ingreso.cfdi_use,
        currency=ingreso.currency,
        subtotal_cents=subtotal_cents,
        iva_cents=amount_cents - subtotal_cents,
        total_cents=amount_cents,
        pac_vendor=result.pac_vendor,
        xml_path=_persist_xml(result.uuid, result.xml),
        stamped_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    try:
        db.commit()
    except IntegrityError:
        # Lost a same-key race past the lock (belt-and-suspenders) — the unique
        # index rejected the duplicate; return the row the winner committed.
        db.rollback()
        existing = _by_idempotency_key(db, idempotency_key)
        if existing is not None:
            return {"document": existing}
        raise
    db.refresh(doc)
    return {"document": doc}


def latest_document(db: Session, order_id: int) -> Optional[CfdiDocument]:
    return (
        db.query(CfdiDocument)
        .filter(CfdiDocument.order_id == order_id)
        .order_by(CfdiDocument.id.desc())
        .first()
    )


def _persist_xml(uuid: str, xml: str) -> Optional[str]:
    """Write the stamped XML to the uploads dir; best-effort (the DB row is
    the source of truth, the file is an artifact)."""
    if not xml:
        return None
    try:
        from pathlib import Path

        base = Path("uploads") / "cfdi"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{uuid}.xml"
        path.write_text(xml, encoding="utf-8")
        return str(path)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist CFDI XML for %s", uuid)
        return None
