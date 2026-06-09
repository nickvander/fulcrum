"""Add products.compare_at_price (public "was"/list price for sale plaques)

Nullable Float; NULL = no sale. A PUBLIC price (not a cost) the storefront shows
struck-through next to the resale price when it's higher. Additive.

Builds linearly on the sole head ``b4d8f2a1c6e9``.

Revision ID: c5e9a3b7f1d2
Revises: b4d8f2a1c6e9
Create Date: 2026-06-08 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5e9a3b7f1d2"
down_revision: Union[str, Sequence[str], None] = "b4d8f2a1c6e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("compare_at_price", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "compare_at_price")
