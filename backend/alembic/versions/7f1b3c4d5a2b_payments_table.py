"""create payments table

First slice of the Mercado Pago Checkout integration. Adds the
`payments` table that records every payment attempt against a
SalesOrder. Provider is keyed for future extension to additional
gateways (Stripe, PayPal) without a schema change.

Unique on (provider, external_payment_id) so a re-received webhook
updates the existing row instead of duplicating it. NULL allowed
because we create the row BEFORE we have the provider's id, so a
create-call failure still has a row to retry from.

Revision ID: 7f1b3c4d5a2b
Revises: 6e0a4c5d2f19
Create Date: 2026-05-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f1b3c4d5a2b"
down_revision: Union[str, Sequence[str], None] = "6e0a4c5d2f19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUSES = ("pending", "approved", "rejected", "refunded", "cancelled")


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sales_order_id",
            sa.Integer(),
            sa.ForeignKey("sales_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="mercado_pago"),
        sa.Column("external_payment_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="MXN"),
        sa.Column("payer_email", sa.String(length=255), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("last_webhook_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('" + "','".join(_STATUSES) + "')",
            name="ck_payments_status",
        ),
        sa.UniqueConstraint(
            "provider", "external_payment_id",
            name="uq_payments_provider_external",
        ),
    )
    op.create_index("ix_payments_sales_order_id", "payments", ["sales_order_id"])
    op.create_index("ix_payments_provider", "payments", ["provider"])
    op.create_index("ix_payments_external_payment_id", "payments", ["external_payment_id"])
    op.create_index("ix_payments_status", "payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_external_payment_id", table_name="payments")
    op.drop_index("ix_payments_provider", table_name="payments")
    op.drop_index("ix_payments_sales_order_id", table_name="payments")
    op.drop_table("payments")
