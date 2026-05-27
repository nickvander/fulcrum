"""Widen ck_alert_rules_type to accept the new settlement_variance type

The settlement-variance alert fires when settled marketplace fees
(captured by the Phase-8 settlement-fee ingestion) diverge from
what `Marketplace.default_fee_rate` would predict — catches FBA
overage charges, promo deductions, and quiet billing changes the
operator wouldn't otherwise spot.

We only need to widen the CHECK constraint. No schema additions —
the rule reuses the existing `AlertRule.threshold` column as the
variance threshold (interpreted as a percentage).

Revision ID: 9c4a2d8e5b30
Revises: 8b3f1d5e6c70
Create Date: 2026-05-20 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "9c4a2d8e5b30"
down_revision: Union[str, Sequence[str], None] = "8b3f1d5e6c70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_alert_rules_type", "alert_rules", type_="check")
    op.create_check_constraint(
        "ck_alert_rules_type",
        "alert_rules",
        "alert_type IN ("
        "'low_margin','sales_dip','stockout_risk','refund_rate_spike',"
        "'settlement_variance'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint("ck_alert_rules_type", "alert_rules", type_="check")
    op.create_check_constraint(
        "ck_alert_rules_type",
        "alert_rules",
        "alert_type IN ("
        "'low_margin','sales_dip','stockout_risk','refund_rate_spike'"
        ")",
    )
