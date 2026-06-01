"""add phone column to users

Customer self-service profiles (FP-05) persist a contact phone. Nullable so
existing rows are unaffected and the upgrade is online-safe.

Revision ID: a3f9c1d27b6e
Revises: f1c7a2e9b840
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a3f9c1d27b6e"
down_revision: Union[str, Sequence[str], None] = "f1c7a2e9b840"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
