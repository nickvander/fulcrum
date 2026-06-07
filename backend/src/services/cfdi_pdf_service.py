"""CFDI representación impresa (PDF) — FP-06 P2.

The legally-binding artifact is the stamped XML; this module renders a
human-readable PDF "representación impresa" from the stamped CfdiDocument +
issuer config + order lines, using reportlab (already a dependency). It works
without a live PAC (the mock-stamped flow renders a valid PDF for dev/tests); a
production PDF with the official SAT sello/QR would come from the PAC, but a
self-rendered representación is acceptable and keeps the pipeline testable.

Generated on demand (no storage): money is read from the CfdiDocument (already in
centavos) and line concepts from the order. Centavos → pesos only at render.
"""
from __future__ import annotations

import io
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from src.models.cfdi_document import CfdiDocument
from src.models.order import SalesOrder, SalesOrderItem
from src.services import cfdi_service, cfdi_stamp_service

_RFC_GENERICO = "XAXX010101000"


def _pesos(cents: Optional[int]) -> str:
    return f"${(int(cents or 0) / 100):,.2f}"


def render_pdf(db: Session, order_id: int) -> Optional[bytes]:
    """Render the representación impresa for an order's stamped CFDI.

    Returns the PDF bytes, or None when there is no stamped CFDI for the order.
    """
    doc: Optional[CfdiDocument] = cfdi_stamp_service.latest_document(db, order_id)
    if doc is None or doc.status != "stamped":
        return None

    issuer = cfdi_service.read_issuer_config(db)
    order = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.items).joinedload(SalesOrderItem.product))
        .filter(SalesOrder.id == order_id)
        .first()
    )

    # Imported lazily so a missing optional dep can't break module import.
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 20 * mm
    y = height - 20 * mm

    def line(text: str, *, dy: float = 6 * mm, font: str = "Helvetica", size: int = 10) -> None:
        nonlocal y
        pdf.setFont(font, size)
        pdf.drawString(x, y, text)
        y -= dy

    line("Factura CFDI 4.0 — Representación impresa", font="Helvetica-Bold", size=14, dy=9 * mm)
    line(f"Folio fiscal (UUID): {doc.uuid or '—'}", size=9)
    if doc.stamped_at:
        line(f"Fecha de timbrado: {doc.stamped_at.isoformat()}", size=9)
    line(f"PAC: {doc.pac_vendor or '—'}", size=9, dy=8 * mm)

    # Emisor
    line("Emisor", font="Helvetica-Bold")
    line(f"RFC: {issuer.rfc or '—'}    Régimen: {issuer.tax_regime or '—'}", size=9)
    line(f"Razón social: {issuer.name or '—'}", size=9)
    line(f"Lugar de expedición (CP): {issuer.postal_code or '—'}", size=9, dy=8 * mm)

    # Receptor
    line("Receptor", font="Helvetica-Bold")
    line(f"RFC: {doc.receiver_rfc or _RFC_GENERICO}", size=9)
    line(f"Nombre: {doc.receiver_name or 'Público en general'}", size=9)
    line(
        f"CP fiscal: {doc.receiver_postal_code or '—'}    "
        f"Régimen: {doc.receiver_regime or '—'}    Uso CFDI: {doc.cfdi_use or '—'}",
        size=9,
        dy=8 * mm,
    )

    # Conceptos
    line("Conceptos", font="Helvetica-Bold")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(x, y, "Descripción")
    pdf.drawString(x + 95 * mm, y, "Cant.")
    pdf.drawString(x + 115 * mm, y, "P. unitario")
    pdf.drawString(x + 150 * mm, y, "Importe")
    y -= 5 * mm
    for item in (order.items if order else []) or []:
        name = (item.product.name if item.product else f"Producto {item.product_id}")[:55]
        qty = int(item.quantity or 0)
        unit = float(item.price_per_unit or 0.0)
        amount = unit * qty
        pdf.setFont("Helvetica", 8)
        pdf.drawString(x, y, name)
        pdf.drawString(x + 95 * mm, y, str(qty))
        pdf.drawString(x + 115 * mm, y, f"${unit:,.2f}")
        pdf.drawString(x + 150 * mm, y, f"${amount:,.2f}")
        y -= 5 * mm

    y -= 4 * mm
    line(f"Subtotal: {_pesos(doc.subtotal_cents)} {doc.currency or 'MXN'}", size=9, dy=5 * mm)
    line(f"IVA: {_pesos(doc.iva_cents)} {doc.currency or 'MXN'}", size=9, dy=5 * mm)
    line(
        f"Total: {_pesos(doc.total_cents)} {doc.currency or 'MXN'}",
        font="Helvetica-Bold",
        size=11,
        dy=10 * mm,
    )

    pdf.setFont("Helvetica-Oblique", 7)
    pdf.drawString(
        x,
        y,
        "Este documento es una representación impresa de un CFDI. El XML timbrado es el comprobante fiscal válido.",
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
