"""add whatsapp opt-in consent columns to users

Transactional WhatsApp (and future channel) sends require a recorded, timestamped
opt-in (WhatsApp policy + LFPDPPP). Consent lives on the customer master (the
``users`` row), so the storefront BFF gates every send on it. Both columns are
online-safe: ``whatsapp_opt_in`` defaults to false for existing rows;
``whatsapp_opt_in_at`` is nullable.

Revision ID: c5e9a1f0d3b2
Revises: d3f7a1c8e024
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c5e9a1f0d3b2"
down_revision: Union[str, Sequence[str], None] = "d3f7a1c8e024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "whatsapp_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "whatsapp_opt_in_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "whatsapp_opt_in_at")
    op.drop_column("users", "whatsapp_opt_in")
