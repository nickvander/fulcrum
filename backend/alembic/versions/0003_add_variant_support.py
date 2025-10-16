"""Add variant support to inventory and product variants

Revision ID: 0003_add_variant_support
Revises: 0002_add_inventory_adjustments
Create Date: 2025-10-16 08:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime


# revision identifiers, used by Alembic.
revision: str = '0003_add_variant_support'
down_revision: Union[str, None] = '0002_add_inventory_adjustments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create product_variants table first
    op.create_table('product_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sku', sa.String(), nullable=True),  # Make nullable to allow creating index
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('cost_price', sa.Float(), nullable=True),
        sa.Column('attributes', sa.String(), nullable=True),
        sa.Column('created_at', DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_variants_id'), 'product_variants', ['id'], unique=False)
    op.create_index(op.f('ix_product_variants_sku'), 'product_variants', ['sku'], unique=True)
    op.create_index(op.f('ix_product_variants_product_id'), 'product_variants', ['product_id'], unique=False)

    # Add variant_id column to inventory_items table
    op.add_column('inventory_items', sa.Column('variant_id', sa.Integer(), nullable=True))
    op.add_column('inventory_items', sa.Column('created_at', DateTime(), nullable=True))
    op.add_column('inventory_items', sa.Column('updated_at', DateTime(), nullable=True))
    
    # Update inventory_items table to allow nullable product_id for variant-only inventory
    # First drop the existing foreign key constraint on product_id
    op.drop_constraint('inventory_items_product_id_fkey', 'inventory_items', type_='foreignkey')
    # Then alter the column to allow nulls
    op.alter_column('inventory_items', 'product_id', nullable=True)
    # Then recreate the foreign key constraint allowing nulls
    op.create_foreign_key('fk_inventory_items_product_id', 'inventory_items', 'products', ['product_id'], ['id'], ondelete='CASCADE')
    # Add the foreign key constraint for variant_id
    op.create_foreign_key('fk_inventory_items_variant_id', 'inventory_items', 'product_variants', ['variant_id'], ['id'], ondelete='CASCADE')

    # Add variant_id column to inventory_adjustments table (created_by already exists from 0002 migration)
    op.add_column('inventory_adjustments', sa.Column('variant_id', sa.Integer(), nullable=True))
    op.add_column('inventory_adjustments', sa.Column('created_at', DateTime(), nullable=True))  # Add the new created_at column

    # Update inventory_adjustments table to allow nullable product_id for variant-only adjustments
    # First drop the existing foreign key constraint on product_id
    op.drop_constraint('inventory_adjustments_product_id_fkey', 'inventory_adjustments', type_='foreignkey')
    # Then alter the column to allow nulls
    op.alter_column('inventory_adjustments', 'product_id', nullable=True)
    # Then recreate the foreign key constraint allowing nulls
    op.create_foreign_key('fk_inventory_adjustments_product_id', 'inventory_adjustments', 'products', ['product_id'], ['id'], ondelete='CASCADE')
    # Add the foreign key constraint for variant_id
    op.create_foreign_key('fk_inventory_adjustments_variant_id', 'inventory_adjustments', 'product_variants', ['variant_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove foreign key constraints first
    op.drop_constraint('fk_inventory_adjustments_variant_id', 'inventory_adjustments', type_='foreignkey')
    op.drop_constraint('fk_inventory_adjustments_product_id', 'inventory_adjustments', type_='foreignkey')
    op.drop_constraint('fk_inventory_items_variant_id', 'inventory_items', type_='foreignkey')
    op.drop_constraint('fk_inventory_items_product_id', 'inventory_items', type_='foreignkey')
    
    # Drop product_variants table
    op.drop_table('product_variants')
    
    # Remove variant_id column from inventory_adjustments
    op.drop_column('inventory_adjustments', 'variant_id')
    op.drop_column('inventory_adjustments', 'created_at')
    
    # Restore the original product_id constraint for inventory_adjustments
    op.alter_column('inventory_adjustments', 'product_id', nullable=False)
    op.create_foreign_key('inventory_adjustments_product_id_fkey', 'inventory_adjustments', 'products', ['product_id'], ['id'])
    
    # Remove variant_id column from inventory_items
    op.drop_column('inventory_items', 'variant_id')
    op.drop_column('inventory_items', 'created_at')
    op.drop_column('inventory_items', 'updated_at')
    
    # Restore the original product_id constraint for inventory_items
    op.alter_column('inventory_items', 'product_id', nullable=False)
    op.create_foreign_key('inventory_items_product_id_fkey', 'inventory_items', 'products', ['product_id'], ['id'])