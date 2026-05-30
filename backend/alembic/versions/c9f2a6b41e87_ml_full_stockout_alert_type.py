"""ml_full_stockout_risk alert type

Admit the new `ml_full_stockout_risk` AlertType into the
`ck_alert_rules_type` CHECK constraint. Same string-column + CHECK
pattern as every prior alert type (no PG enum), so this is a
drop-and-recreate of the constraint with one added value.

Revision ID: c9f2a6b41e87
Revises: b8e4f1a7c623
Create Date: 2026-05-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c9f2a6b41e87"
down_revision: Union[str, Sequence[str], None] = "b8e4f1a7c623"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT = "ck_alert_rules_type"

_TYPES_OLD = (
    "low_margin", "sales_dip", "stockout_risk",
    "refund_rate_spike", "settlement_variance",
)
_TYPES_NEW = _TYPES_OLD + ("ml_full_stockout_risk",)


def _clause(types: tuple[str, ...]) -> str:
    return "alert_type IN ('" + "','".join(types) + "')"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "alert_rules", type_="check")
    op.create_check_constraint(_CONSTRAINT, "alert_rules", _clause(_TYPES_NEW))


def downgrade() -> None:
    # Drop any rules using the new type before narrowing the constraint
    # so the re-applied CHECK doesn't fail on existing rows.
    op.execute("DELETE FROM alert_rules WHERE alert_type = 'ml_full_stockout_risk'")
    op.drop_constraint(_CONSTRAINT, "alert_rules", type_="check")
    op.create_check_constraint(_CONSTRAINT, "alert_rules", _clause(_TYPES_OLD))
