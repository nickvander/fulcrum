"""Returns Phase 2: sales_order_returns.restock (restocking rule)

Adds a NOT NULL ``restock`` boolean (server_default true) recording whether a
return's units go back to sellable inventory on approval. Decided at request
time from the reason (defective/damaged → false); operator-recorded returns
default true. Additive; existing rows backfill to true (their stock was already
credited under the prior always-restock behavior).

Builds linearly on the sole head ``a3c7e1f9b2d4``.

Revision ID: b4d8f2a1c6e9
Revises: a3c7e1f9b2d4
Create Date: 2026-06-08 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d8f2a1c6e9"
down_revision: Union[str, Sequence[str], None] = "a3c7e1f9b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_order_returns",
        sa.Column(
            "restock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("sales_order_returns", "restock")
