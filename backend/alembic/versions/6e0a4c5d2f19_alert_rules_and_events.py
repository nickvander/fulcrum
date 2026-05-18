"""create alert_rules + alert_events

Adds the schema backing the Track 3 / Step 6 alerting work: per-user
configurable rules for low margin, sales dips, and stockout risk, plus
a history table for audit + "why didn't I get an email" debugging.

`alert_type` is a plain VARCHAR with a CHECK constraint instead of a
PG enum — the SQLAlchemy enum/ENUM autocreate dance is brittle, and
the Pydantic schema enforces the same values at the API boundary so
the DB-level check is just a safety net.

Revision ID: 6e0a4c5d2f19
Revises: 5d9f2a3b1c08
Create Date: 2026-05-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e0a4c5d2f19"
down_revision: Union[str, Sequence[str], None] = "5d9f2a3b1c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ALERT_TYPES = ("low_margin", "sales_dip", "stockout_risk")


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="720"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_email", sa.String(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "alert_type IN ('" + "','".join(_ALERT_TYPES) + "')",
            name="ck_alert_rules_type",
        ),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])
    op.create_index("ix_alert_rules_alert_type", "alert_rules", ["alert_type"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "alert_rule_id",
            sa.Integer(),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_alert_events_alert_rule_id", "alert_events", ["alert_rule_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_alert_rule_id", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_alert_rules_alert_type", table_name="alert_rules")
    op.drop_index("ix_alert_rules_user_id", table_name="alert_rules")
    op.drop_table("alert_rules")
