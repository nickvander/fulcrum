"""add supplier_products table

Revision ID: 0008_add_supplier_products
Revises: 0007_add_cost_breakdown_fields
Create Date: 2025-12-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008_add_supplier_products'
down_revision: Union[str, None] = '0007_add_cost_breakdown_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'supplier_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('supplier_sku', sa.String(), nullable=True),
        sa.Column('cost_price', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('minimum_order_qty', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('last_ordered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_supplier_products_id', 'supplier_products', ['id'])
    op.create_index('ix_supplier_products_supplier_sku', 'supplier_products', ['supplier_sku'])
    # Unique constraint on product_id + supplier_id
    op.create_unique_constraint(
        'uq_supplier_product',
        'supplier_products',
        ['product_id', 'supplier_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_supplier_product', 'supplier_products', type_='unique')
    op.drop_index('ix_supplier_products_supplier_sku', table_name='supplier_products')
    op.drop_index('ix_supplier_products_id', table_name='supplier_products')
    op.drop_table('supplier_products')
