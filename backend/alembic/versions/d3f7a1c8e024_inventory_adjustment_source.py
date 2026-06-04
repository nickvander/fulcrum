"""inventory_adjustment structured source + source_id

Add `source` (machine key, e.g. 'purchase_order') and `source_id`
(originating entity id, e.g. PurchaseOrder.id) to `inventory_adjustments`
so the stock-history UI can deep-link an adjustment to its origin
without string-matching the localized free-text `reason` (the old
`reason.startsWith('Received PO #')` was an i18n landmine).

Both columns are NULL on legacy rows and on adjustments with no
structured origin (manual edits). `source` is indexed for
"everything that came from PO receiving" style queries. Deliberately
NOT CHECK-constrained — unlike `reason_code`, `source` is an open set
that should grow with new write paths without a migration each time.

Revision ID: d3f7a1c8e024
Revises: b7e1c0d4f206
Create Date: 2026-06-04 06:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d3f7a1c8e024"
down_revision: Union[str, Sequence[str], None] = "b7e1c0d4f206"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory_adjustments",
        sa.Column("source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "inventory_adjustments",
        sa.Column("source_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_inventory_adjustments_source"),
        "inventory_adjustments",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_adjustments_source"),
        table_name="inventory_adjustments",
    )
    op.drop_column("inventory_adjustments", "source_id")
    op.drop_column("inventory_adjustments", "source")
