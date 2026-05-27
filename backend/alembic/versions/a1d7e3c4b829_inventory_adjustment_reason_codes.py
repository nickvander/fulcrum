"""inventory_adjustment reason_code column

Add a typed `reason_code` enum column to `inventory_adjustments` so
the audit log can be filtered by *why* stock moved (shrinkage,
recount, damage, return, theft, correction, sale, cancellation,
transfer, manual, other) instead of just by free-text. The existing
`reason` column stays as the free-form note — `reason_code` is the
operator-actionable taxonomy that drives the audit-page filter and
the future "how much did I lose to shrinkage last month?" reports.

Legacy rows have `reason_code = NULL`; the audit filter treats NULL
as "uncategorized" and shows it as such. Going forward every
`InventoryService.adjust_stock` call site sets it explicitly.

Indexed because the audit page's most common filter is by reason
code over a date window.

Revision ID: a1d7e3c4b829
Revises: 9c4a2d8e5b30
Create Date: 2026-05-20 06:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1d7e3c4b829"
down_revision: Union[str, Sequence[str], None] = "9c4a2d8e5b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Kept in sync with `InventoryAdjustmentReasonCode` in
# `src/models/inventory.py`. The CHECK constraint mirrors the AlertType
# pattern (string column + CHECK, no PG enum type — keeps the
# add-a-new-code migration a single ALTER instead of a USING cast).
_REASON_CODES = (
    "shrinkage",
    "recount",
    "damage",
    "return",
    "theft",
    "correction",
    "sale",
    "cancellation",
    "transfer",
    "purchase",
    "manual",
    "other",
)


def upgrade() -> None:
    op.add_column(
        "inventory_adjustments",
        sa.Column("reason_code", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_inventory_adjustments_reason_code",
        "inventory_adjustments",
        "reason_code IS NULL OR reason_code IN ('"
        + "','".join(_REASON_CODES)
        + "')",
    )
    op.create_index(
        op.f("ix_inventory_adjustments_reason_code"),
        "inventory_adjustments",
        ["reason_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_adjustments_reason_code"),
        table_name="inventory_adjustments",
    )
    op.drop_constraint(
        "ck_inventory_adjustments_reason_code",
        "inventory_adjustments",
        type_="check",
    )
    op.drop_column("inventory_adjustments", "reason_code")
