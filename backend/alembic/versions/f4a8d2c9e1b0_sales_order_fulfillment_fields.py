"""add fulfillment fields to sales_orders

Vendio's storefront BFF quotes and buys shipping labels, but Fulcrum owns
the order. These nullable fields let Fulcrum persist the selected shipping
charge and purchased label metadata directly on the SalesOrder row without
introducing a second order master.

Revision ID: f4a8d2c9e1b0
Revises: a3f9c1d27b6e
Create Date: 2026-06-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a8d2c9e1b0"
down_revision: Union[str, Sequence[str], None] = "a3f9c1d27b6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column("shipping_rate_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_carrier", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_service", sa.String(length=128), nullable=True),
    )
    op.add_column("sales_orders", sa.Column("shipping_cost", sa.Float(), nullable=True))
    op.add_column(
        "sales_orders",
        sa.Column("shipping_currency", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_estimated_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "shipping_charge_idempotency_key", sa.String(length=128), nullable=True
        ),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_shipment_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("shipping_tracking_number", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sales_orders", sa.Column("shipping_label_url", sa.String(), nullable=True)
    )
    op.add_column(
        "sales_orders", sa.Column("shipping_tracking_url", sa.String(), nullable=True)
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "shipping_label_idempotency_key", sa.String(length=128), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "shipping_label_idempotency_key")
    op.drop_column("sales_orders", "shipping_tracking_url")
    op.drop_column("sales_orders", "shipping_label_url")
    op.drop_column("sales_orders", "shipping_tracking_number")
    op.drop_column("sales_orders", "shipping_shipment_id")
    op.drop_column("sales_orders", "shipping_charge_idempotency_key")
    op.drop_column("sales_orders", "shipping_estimated_days")
    op.drop_column("sales_orders", "shipping_currency")
    op.drop_column("sales_orders", "shipping_cost")
    op.drop_column("sales_orders", "shipping_service")
    op.drop_column("sales_orders", "shipping_carrier")
    op.drop_column("sales_orders", "shipping_provider")
    op.drop_column("sales_orders", "shipping_rate_id")
