"""order_cost_breakdowns + marketplace fee config + sales_orders.currency

Track 1 of Phase 8 Advanced Analytics — sets up the data model for
the per-order cost engine. The breakdown row is 1:1 with SalesOrder,
held in a separate `order_cost_breakdowns` table so a recompute
doesn't have to touch the OLTP `sales_orders` row.

Three things land together because they're tightly coupled:

  - `marketplaces.default_fee_rate` / `default_shipping_cost`: the
    cost engine reads these to estimate fees / shipping when the
    marketplace's API doesn't carry per-order fee data. Both are
    fractions / amounts in the marketplace's currency. Default 0.0
    so engine output exactly matches the existing margin report for
    older orders until the operator configures real rates.

  - `sales_orders.currency`: needed for currency normalization in the
    breakdown. Defaults to 'MXN' for back-compat — Mexico is the
    primary market and every existing order is implicitly MXN.

  - `order_cost_breakdowns`: the analytics row itself. Unique on
    `order_id` so a recompute upserts cleanly. Index on
    `computed_at` so the backfill beat can find stale rows cheaply.

Revision ID: 4f7a9c1e3b22
Revises: 9b2d3e7a5f01
Create Date: 2026-05-18 19:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4f7a9c1e3b22"
down_revision: Union[str, Sequence[str], None] = "9b2d3e7a5f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "marketplaces",
        sa.Column(
            "default_fee_rate",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "marketplaces",
        sa.Column(
            "default_shipping_cost",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "currency",
            sa.String(length=8),
            nullable=False,
            server_default="MXN",
        ),
    )

    op.create_table(
        "order_cost_breakdowns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="MXN"),
        sa.Column("exchange_rate_to_mxn", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("revenue_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("revenue_amount_mxn", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cogs_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("marketplace_fees_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("shipping_cost_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ad_spend_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("other_cost_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_profit_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_margin_percent", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_order_cost_breakdowns_order_id"),
    )
    op.create_index(
        "ix_order_cost_breakdowns_computed_at",
        "order_cost_breakdowns",
        ["computed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_order_cost_breakdowns_computed_at",
        table_name="order_cost_breakdowns",
    )
    op.drop_table("order_cost_breakdowns")
    op.drop_column("sales_orders", "currency")
    op.drop_column("marketplaces", "default_shipping_cost")
    op.drop_column("marketplaces", "default_fee_rate")
