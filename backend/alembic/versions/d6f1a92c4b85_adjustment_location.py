"""inventory_adjustments.location column

Adds a per-row `location` to the inventory audit so the shrinkage /
reason-code rollup can answer "where am I bleeding stock?" per
warehouse / shelf. Without this column we'd have to join back
through `inventory_items` to guess, which is ambiguous for SKUs
stocked at multiple locations.

Backfill behavior:
  - Existing rows get NULL. The report surfaces NULL under an
    "(unknown)" sentinel so the operator can see which historic
    rows pre-date the column.
  - All new rows from `InventoryService.adjust_stock` (every
    semantic caller) stamp the `location` argument the caller
    already passes through.
  - Count-session commits carry `session.location`.

Indexed because the rollup query filters / groups by it.

Revision ID: d6f1a92c4b85
Revises: c5d1e8a3b072
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'd6f1a92c4b85'
down_revision = 'c5d1e8a3b072'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'inventory_adjustments',
        sa.Column('location', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_inventory_adjustments_location',
        'inventory_adjustments',
        ['location'],
    )


def downgrade():
    op.drop_index(
        'ix_inventory_adjustments_location',
        table_name='inventory_adjustments',
    )
    op.drop_column('inventory_adjustments', 'location')
