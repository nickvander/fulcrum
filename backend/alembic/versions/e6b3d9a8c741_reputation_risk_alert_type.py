"""reputation_risk alert type

Admit `reputation_risk` into the `ck_alert_rules_type` CHECK constraint.
Same drop-and-recreate pattern as the prior alert types.

Revision ID: e6b3d9a8c741
Revises: d4a8c1f9e562
Create Date: 2026-05-30 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e6b3d9a8c741"
down_revision: Union[str, Sequence[str], None] = "d4a8c1f9e562"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT = "ck_alert_rules_type"

_TYPES_OLD = (
    "low_margin", "sales_dip", "stockout_risk",
    "refund_rate_spike", "settlement_variance", "ml_full_stockout_risk",
)
_TYPES_NEW = _TYPES_OLD + ("reputation_risk",)


def _clause(types: tuple[str, ...]) -> str:
    return "alert_type IN ('" + "','".join(types) + "')"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "alert_rules", type_="check")
    op.create_check_constraint(_CONSTRAINT, "alert_rules", _clause(_TYPES_NEW))


def downgrade() -> None:
    op.execute("DELETE FROM alert_rules WHERE alert_type = 'reputation_risk'")
    op.drop_constraint(_CONSTRAINT, "alert_rules", type_="check")
    op.create_check_constraint(_CONSTRAINT, "alert_rules", _clause(_TYPES_OLD))
