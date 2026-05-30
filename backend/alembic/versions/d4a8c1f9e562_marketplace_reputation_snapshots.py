"""marketplace_reputation_snapshots table

Persist seller reputation metrics (MercadoLibre `seller_reputation`)
over time so the reputation_risk alert evaluator can read the latest
values from the DB (Celery beat has no marketplace auth context) and the
health page can show a trend.

Revision ID: d4a8c1f9e562
Revises: c9f2a6b41e87
Create Date: 2026-05-30 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4a8c1f9e562"
down_revision: Union[str, Sequence[str], None] = "c9f2a6b41e87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_reputation_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("marketplace_id", sa.Integer(), nullable=True),
        sa.Column("level_id", sa.String(), nullable=True),
        sa.Column("power_seller_status", sa.String(), nullable=True),
        sa.Column("transactions_total", sa.Integer(), nullable=True),
        sa.Column("transactions_completed", sa.Integer(), nullable=True),
        sa.Column("sales_completed", sa.Integer(), nullable=True),
        sa.Column("claims_rate", sa.Float(), nullable=True),
        sa.Column("claims_value", sa.Integer(), nullable=True),
        sa.Column("cancellations_rate", sa.Float(), nullable=True),
        sa.Column("cancellations_value", sa.Integer(), nullable=True),
        sa.Column("delayed_handling_rate", sa.Float(), nullable=True),
        sa.Column("delayed_handling_value", sa.Integer(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column(
            "captured_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"], ["marketplace_credentials.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["marketplace_id"], ["marketplaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketplace_reputation_snapshots_id"),
        "marketplace_reputation_snapshots", ["id"], unique=False,
    )
    op.create_index(
        op.f("ix_marketplace_reputation_snapshots_credential_id"),
        "marketplace_reputation_snapshots", ["credential_id"], unique=False,
    )
    op.create_index(
        op.f("ix_marketplace_reputation_snapshots_captured_at"),
        "marketplace_reputation_snapshots", ["captured_at"], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_marketplace_reputation_snapshots_captured_at"),
        table_name="marketplace_reputation_snapshots",
    )
    op.drop_index(
        op.f("ix_marketplace_reputation_snapshots_credential_id"),
        table_name="marketplace_reputation_snapshots",
    )
    op.drop_index(
        op.f("ix_marketplace_reputation_snapshots_id"),
        table_name="marketplace_reputation_snapshots",
    )
    op.drop_table("marketplace_reputation_snapshots")
