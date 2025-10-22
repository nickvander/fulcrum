"""Initial migration

Revision ID: 0001_initial_migration
Revises: 
Create Date: 2025-10-11 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = '0001_initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Create all tables based on current models
    op.create_table('marketplaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('api_base_url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_marketplaces_id'), 'marketplaces', ['id'], unique=False)
    op.create_index(op.f('ix_marketplaces_name'), 'marketplaces', ['name'], unique=True)

    op.create_table('sales_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('total_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('source', sa.Enum('FULCRUM', 'MERCADOLIBRE', 'AMAZON', name='ordersource', create_type=False), nullable=True),
        sa.Column('external_order_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_orders_id'), 'sales_orders', ['id'], unique=False)

    op.create_table('suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('contact_person', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppliers_email'), 'suppliers', ['email'], unique=True)
    op.create_index(op.f('ix_suppliers_id'), 'suppliers', ['id'], unique=False)
    op.create_index(op.f('ix_suppliers_name'), 'suppliers', ['name'], unique=False)

    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_table('marketplace_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('marketplace_id', sa.Integer(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['marketplace_id'], ['marketplaces.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_marketplace_credentials_id'), 'marketplace_credentials', ['id'], unique=False)

    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('sku', sa.String(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('default_resale_price', sa.Float(), nullable=True),
        sa.Column('cost_price', sa.Float(), nullable=True),
        sa.Column('properties', sa.String(), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.Column('manufacturer', sa.String(), nullable=True),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('depth', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)

    op.create_table('inventory_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_items_id'), 'inventory_items', ['id'], unique=False)

    op.create_table('marketplace_listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('marketplace_id', sa.Integer(), nullable=True),
        sa.Column('external_listing_id', sa.String(), nullable=True),
        sa.Column('listing_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['marketplace_id'], ['marketplaces.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_marketplace_listings_id'), 'marketplace_listings', ['id'], unique=False)

    op.create_table('product_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('is_primary', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_images_id'), 'product_images', ['id'], unique=False)

    op.create_table('sales_order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('price_per_unit', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['sales_orders.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_order_items_id'), 'sales_order_items', ['id'], unique=False)

    # Create ENUM type for custom fields if it doesn't exist
    op.create_table('custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('type', sa.Enum('TEXT', 'NUMBER', 'BOOLEAN', 'DATE', name='fieldtype'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_custom_fields_id'), 'custom_fields', ['id'], unique=False)
    op.create_index(op.f('ix_custom_fields_name'), 'custom_fields', ['name'], unique=True)

    op.create_table('product_custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('custom_field_id', sa.Integer(), nullable=True),
        sa.Column('value', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['custom_field_id'], ['custom_fields.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_custom_fields_id'), 'product_custom_fields', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse dependency order with IF EXISTS to handle cases where tables might not exist
    op.execute('DROP TABLE IF EXISTS product_custom_fields')
    op.execute('DROP TABLE IF EXISTS product_images')
    op.execute('DROP TABLE IF EXISTS marketplace_listings')
    op.execute('DROP TABLE IF EXISTS inventory_items')
    op.execute('DROP TABLE IF EXISTS sales_order_items')
    op.execute('DROP TABLE IF EXISTS marketplace_credentials')
    
    # Drop main tables after related tables are removed
    op.execute('DROP TABLE IF EXISTS products')
    op.execute('DROP TABLE IF EXISTS users')
    op.execute('DROP TABLE IF EXISTS suppliers')
    op.execute('DROP TABLE IF EXISTS sales_orders')
    op.execute('DROP TABLE IF EXISTS marketplaces')
    
    # Drop lookup tables last
    op.execute('DROP TABLE IF EXISTS custom_fields')
    op.execute('DROP TYPE IF EXISTS fieldtype')