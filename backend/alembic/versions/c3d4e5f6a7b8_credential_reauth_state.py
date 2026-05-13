"""add_reauthorization_state_to_marketplace_credentials

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-12 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketplace_credentials",
        sa.Column(
            "needs_reauthorization",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "marketplace_credentials",
        sa.Column("last_refresh_error", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketplace_credentials", "last_refresh_error")
    op.drop_column("marketplace_credentials", "needs_reauthorization")
