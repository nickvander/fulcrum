"""FP-11 hardening: api_keys.scope (least-privilege integration keys)

Adds ``api_keys.scope`` — a coarse permission so a key can be minted read-only.
Defaults to ``"full"`` (read+write) so every EXISTING key keeps working; a
``"read_only"`` key is rejected on write endpoints (require_write_scope).

Additive with a safe server default — no backfill, no behavior change for
existing rows. Builds linearly on the sole head ``d8b3f1a52c47``.

Revision ID: e1a2b3c4d5f6
Revises: d8b3f1a52c47
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1a2b3c4d5f6"
down_revision: Union[str, Sequence[str], None] = "d8b3f1a52c47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("scope", sa.String(), nullable=False, server_default="full"),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "scope")
