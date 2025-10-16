"""Add inventory_adjustments table

Revision ID: 0002_add_inventory_adjustments
Revises: 0001_initial_migration
Create Date: 2025-10-14 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '0002_add_inventory_adjustments'
down_revision: Union[str, None] = '0001_initial_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create inventory_adjustments table
    op.create_table('inventory_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('adjustment', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('timestamp', DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_adjustments_id'), 'inventory_adjustments', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_adjustments_product_id'), 'inventory_adjustments', ['product_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP TABLE IF EXISTS inventory_adjustments')