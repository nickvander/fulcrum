"""CFDI fiscal document (FP-06).

One row per issued or linked CFDI: a sale (`ingreso`), a credit note
(`egreso` / nota de crédito), or a `global` factura spanning many orders.
`invoicing_source` distinguishes documents Fulcrum stamped via a PAC
(`self`) from ones issued elsewhere and merely linked here
(`marketplace_handled`, e.g. MercadoLibre's automatic facturación).
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from .base import Base


class CfdiDocument(Base):
    __tablename__ = "cfdi_documents"

    id = Column(Integer, primary_key=True, index=True)
    # NULL for a factura global spanning many orders.
    order_id = Column(
        Integer, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind = Column(String(16), nullable=False, default="ingreso", server_default="ingreso")
    status = Column(
        String(16), nullable=False, default="pending", server_default="pending", index=True
    )
    invoicing_source = Column(
        String(24), nullable=False, default="self", server_default="self"
    )
    uuid = Column(String(64), nullable=True, unique=True, index=True)
    related_uuid = Column(String(64), nullable=True)  # nota de crédito -> original

    receiver_rfc = Column(String(13), nullable=True)
    receiver_name = Column(String(255), nullable=True)
    receiver_postal_code = Column(String(5), nullable=True)
    receiver_regime = Column(String(8), nullable=True)
    cfdi_use = Column(String(8), nullable=True)

    currency = Column(String(8), nullable=False, default="MXN", server_default="MXN")
    # Amounts in centavos on the PAC path.
    subtotal_cents = Column(Integer, nullable=False, default=0, server_default="0")
    iva_cents = Column(Integer, nullable=False, default=0, server_default="0")
    total_cents = Column(Integer, nullable=False, default=0, server_default="0")

    pac_vendor = Column(String(24), nullable=True)
    xml_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    error_detail = Column(String(500), nullable=True)

    stamped_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
