"""stock_transfer_last_reconciled_at

Adds `last_reconciled_at` to `stock_transfers`. Used by the inbound
reconciliation service (`services/inbound_shipment_reconciliation.py`)
to surface "Last reconciled: X ago" in the stock-transfer detail UI.

Revision ID: 9b2d3e7a5f01
Revises: 7f1b3c4d5a2b
Create Date: 2026-05-18 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9b2d3e7a5f01"
down_revision: Union[str, Sequence[str], None] = "7f1b3c4d5a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "stock_transfers",
        sa.Column(
            "last_reconciled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("stock_transfers", "last_reconciled_at")
