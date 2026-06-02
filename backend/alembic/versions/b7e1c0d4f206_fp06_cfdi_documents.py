"""FP-06: cfdi_documents + per-order CFDI receiver fields

Live CFDI 4.0 stamping (FP-06). `cfdi_documents` stores each issued or
linked fiscal document (its UUID/folio, stamped XML/PDF refs, status,
cancellations, nota-de-crédito links). Per-order receiver columns on
`sales_orders` hold the buyer's fiscal data captured at checkout (absent
=> público en general). All nullable + additive — safe on existing rows.

Revision ID: b7e1c0d4f206
Revises: f4a8d2c9e1b0
Create Date: 2026-06-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e1c0d4f206"
down_revision: Union[str, Sequence[str], None] = "f4a8d2c9e1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-order receiver fiscal capture (NULL => público en general).
    op.add_column("sales_orders", sa.Column("cfdi_receiver_rfc", sa.String(length=13), nullable=True))
    op.add_column("sales_orders", sa.Column("cfdi_receiver_name", sa.String(length=255), nullable=True))
    op.add_column("sales_orders", sa.Column("cfdi_receiver_postal_code", sa.String(length=5), nullable=True))
    op.add_column("sales_orders", sa.Column("cfdi_receiver_regime", sa.String(length=8), nullable=True))
    op.add_column("sales_orders", sa.Column("cfdi_use", sa.String(length=8), nullable=True))

    op.create_table(
        "cfdi_documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        # NULL order_id for a factura global spanning many orders.
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True),
        # 'ingreso' (sale) | 'egreso' (nota de crédito) | 'global'
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="ingreso"),
        # 'stamped' | 'cancelled' | 'pending' | 'error'
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", index=True),
        # 'self' (Fulcrum stamped via PAC) | 'marketplace_handled' (linked, e.g. ML)
        sa.Column("invoicing_source", sa.String(length=24), nullable=False, server_default="self"),
        sa.Column("uuid", sa.String(length=64), nullable=True, unique=True, index=True),
        sa.Column("related_uuid", sa.String(length=64), nullable=True),  # nota de crédito -> original
        sa.Column("receiver_rfc", sa.String(length=13), nullable=True),
        sa.Column("receiver_name", sa.String(length=255), nullable=True),
        sa.Column("receiver_postal_code", sa.String(length=5), nullable=True),
        sa.Column("receiver_regime", sa.String(length=8), nullable=True),
        sa.Column("cfdi_use", sa.String(length=8), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="MXN"),
        # Amounts in centavos on the PAC path.
        sa.Column("subtotal_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iva_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pac_vendor", sa.String(length=24), nullable=True),
        sa.Column("xml_path", sa.String(), nullable=True),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("error_detail", sa.String(length=500), nullable=True),
        sa.Column("stamped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cfdi_documents")
    op.drop_column("sales_orders", "cfdi_use")
    op.drop_column("sales_orders", "cfdi_receiver_regime")
    op.drop_column("sales_orders", "cfdi_receiver_postal_code")
    op.drop_column("sales_orders", "cfdi_receiver_name")
    op.drop_column("sales_orders", "cfdi_receiver_rfc")
