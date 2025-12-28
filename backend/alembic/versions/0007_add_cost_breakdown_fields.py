"""add cost breakdown fields to purchase order items

Revision ID: 0007_add_cost_breakdown_fields
Revises: f49850b583ab
Create Date: 2025-12-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_add_cost_breakdown_fields'
down_revision: Union[str, None] = '425e369a5cfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cost breakdown fields to purchase_order_items
    op.add_column('purchase_order_items', sa.Column('base_cost', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('purchase_order_items', sa.Column('shipping_allocated', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('purchase_order_items', sa.Column('taxes_allocated', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('purchase_order_items', sa.Column('other_allocated', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('purchase_order_items', sa.Column('costs_applied_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('purchase_order_items', 'costs_applied_at')
    op.drop_column('purchase_order_items', 'other_allocated')
    op.drop_column('purchase_order_items', 'taxes_allocated')
    op.drop_column('purchase_order_items', 'shipping_allocated')
    op.drop_column('purchase_order_items', 'base_cost')
