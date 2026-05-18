"""add last_orders_polled_at to marketplace_credentials

Adds a per-credential cursor used by the Amazon order ingestion worker
(and any future polling worker) so each poll only pulls the delta since
the last successful run.

Nullable on purpose: existing credentials default to NULL, which the
ingestion service treats as "no cursor yet → use the connector's 24h
default lookback". Set to the wall clock at the end of each successful
poll. Not advanced on failure.

Revision ID: 4c8f1d2e9b07
Revises: 3b4f7a92e1c2
Create Date: 2026-05-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c8f1d2e9b07"
down_revision: Union[str, Sequence[str], None] = "3b4f7a92e1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketplace_credentials",
        sa.Column("last_orders_polled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketplace_credentials", "last_orders_polled_at")
