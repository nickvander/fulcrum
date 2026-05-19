"""settlement_fee_source on order_cost_breakdowns + per-credential last_settlement_synced_at

Phase 8 Track 1 follow-up: replace estimated marketplace fees with
real settled fees fetched from the marketplace finance API. Two new
columns land together:

  - `order_cost_breakdowns.fees_source` — enum ('estimated' | 'settled').
    Defaults to 'estimated' so back-fill of legacy rows is a no-op.
    When the settlement worker writes real fee data, it flips this to
    'settled'. The cost engine treats 'settled' rows as read-only for
    `marketplace_fees_amount` + `shipping_cost_amount` — a subsequent
    recompute can still refresh COGS (which depends on local product
    cost) without clobbering the real settled fees from the marketplace.

  - `order_cost_breakdowns.fees_synced_at` — timestamp of the last
    settlement write. NULL while the row carries only estimates.
    Surfaced on the marketplace health page so the operator can tell
    at a glance how fresh the settled numbers are.

  - `marketplace_credentials.last_settlement_synced_at` — cursor for
    the settlement-fee poller, mirroring `last_orders_polled_at`. Each
    poll persists "we synced through this timestamp" so the next tick
    only fetches new/updated orders.

Revision ID: 7c2e8d4a91f6
Revises: 4f7a9c1e3b22
Create Date: 2026-05-18 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7c2e8d4a91f6"
down_revision: Union[str, Sequence[str], None] = "4f7a9c1e3b22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_cost_breakdowns",
        sa.Column(
            "fees_source",
            sa.String(length=16),
            nullable=False,
            server_default="estimated",
        ),
    )
    op.add_column(
        "order_cost_breakdowns",
        sa.Column(
            "fees_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_order_cost_breakdowns_fees_source"),
        "order_cost_breakdowns",
        ["fees_source"],
        unique=False,
    )
    op.add_column(
        "marketplace_credentials",
        sa.Column(
            "last_settlement_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("marketplace_credentials", "last_settlement_synced_at")
    op.drop_index(
        op.f("ix_order_cost_breakdowns_fees_source"),
        table_name="order_cost_breakdowns",
    )
    op.drop_column("order_cost_breakdowns", "fees_synced_at")
    op.drop_column("order_cost_breakdowns", "fees_source")
