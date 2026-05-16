"""backfill product.is_bundle and set NOT NULL + server default

Revision ID: 4d2c8a01b9f3
Revises: d4e5f6a7b8c9
Create Date: 2026-05-16 09:55:00.000000

Older product rows had `is_bundle = NULL` because the column had only a
Python-side default; rows inserted via raw SQL (seed scripts, fixtures)
left it null. The product response schema declares `is_bundle: bool`, so
FastAPI returns a 500 ResponseValidationError when serializing those
rows. Backfill the nulls, then enforce NOT NULL with a server default so
future rows can never reproduce the issue.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d2c8a01b9f3"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE products SET is_bundle = false WHERE is_bundle IS NULL")
    op.alter_column(
        "products",
        "is_bundle",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "is_bundle",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
