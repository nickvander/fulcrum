"""add cost_per_unit to sales_order_items

Adds a per-line cost captured at order-create time so the margin
report stops drifting when the buyer updates Product.cost_price after
a sale has already shipped.

NULL = legacy row (or order ingested before this migration). The
margin SQL uses COALESCE(sales_order_items.cost_per_unit,
products.cost_price), so legacy rows keep their old behaviour and new
rows lock in the cost at sale-time.

Revision ID: 5d9f2a3b1c08
Revises: 4c8f1d2e9b07
Create Date: 2026-05-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5d9f2a3b1c08"
down_revision: Union[str, Sequence[str], None] = "4c8f1d2e9b07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_order_items",
        sa.Column("cost_per_unit", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sales_order_items", "cost_per_unit")
