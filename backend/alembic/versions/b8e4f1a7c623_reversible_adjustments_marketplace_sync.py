"""reversible inventory adjustments + marketplace_sync reason code

Two additive changes to `inventory_adjustments`, both in service of the
stock-movement audit feature:

  1. **`reverses_adjustment_id`** — a self-referential FK so a
     correction row can point back at the operator adjustment it
     undoes. `unique=True` enforces the "reverse at most once" rule at
     the DB layer (a second reversal of the same row hits the unique
     constraint). `ON DELETE SET NULL` so a product cascade-delete that
     removes the original doesn't orphan the reversal.

  2. **`marketplace_sync` reason code** — the marketplace listing
     sync/import path used to write audit rows with a NULL reason_code
     ("uncategorized"). It now classifies them as `marketplace_sync`,
     so the CHECK constraint has to admit the new value. Mirrors the
     AlertType pattern: drop + recreate the CHECK, no PG enum type.

Revision ID: b8e4f1a7c623
Revises: f3b6c1d92a47
Create Date: 2026-05-30 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b8e4f1a7c623"
down_revision: Union[str, Sequence[str], None] = "f3b6c1d92a47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT = "ck_inventory_adjustments_reason_code"

# Kept in sync with `InventoryAdjustmentReasonCode` in
# `src/models/inventory.py`.
_REASON_CODES_OLD = (
    "shrinkage", "recount", "damage", "return", "theft", "correction",
    "sale", "cancellation", "transfer", "purchase", "manual", "other",
)
_REASON_CODES_NEW = (
    "shrinkage", "recount", "damage", "return", "theft", "correction",
    "sale", "cancellation", "transfer", "purchase", "marketplace_sync",
    "manual", "other",
)


def _check_clause(codes: tuple[str, ...]) -> str:
    return "reason_code IS NULL OR reason_code IN ('" + "','".join(codes) + "')"


def upgrade() -> None:
    # 1. Self-referential reversal link.
    op.add_column(
        "inventory_adjustments",
        sa.Column("reverses_adjustment_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_adjustments_reverses",
        "inventory_adjustments",
        "inventory_adjustments",
        ["reverses_adjustment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_inventory_adjustments_reverses_adjustment_id"),
        "inventory_adjustments",
        ["reverses_adjustment_id"],
        unique=True,
    )

    # 2. Extend the reason-code CHECK to admit `marketplace_sync`.
    op.drop_constraint(_CONSTRAINT, "inventory_adjustments", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "inventory_adjustments", _check_clause(_REASON_CODES_NEW)
    )


def downgrade() -> None:
    # Revert the CHECK first (NULL out any marketplace_sync rows so the
    # narrower constraint can be re-applied without a violation).
    op.execute(
        "UPDATE inventory_adjustments SET reason_code = NULL "
        "WHERE reason_code = 'marketplace_sync'"
    )
    op.drop_constraint(_CONSTRAINT, "inventory_adjustments", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "inventory_adjustments", _check_clause(_REASON_CODES_OLD)
    )

    op.drop_index(
        op.f("ix_inventory_adjustments_reverses_adjustment_id"),
        table_name="inventory_adjustments",
    )
    op.drop_constraint(
        "fk_inventory_adjustments_reverses",
        "inventory_adjustments",
        type_="foreignkey",
    )
    op.drop_column("inventory_adjustments", "reverses_adjustment_id")
