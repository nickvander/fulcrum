"""add_reorder_point_and_quantity_to_products

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("reorder_point", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("reorder_quantity", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "reorder_quantity")
    op.drop_column("products", "reorder_point")
