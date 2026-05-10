"""add_product_listing_performance_indexes

Revision ID: 8a7c2d4f9b31
Revises: d9aa93dc6f66
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8a7c2d4f9b31"
down_revision: Union[str, Sequence[str], None] = "d9aa93dc6f66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_inventory_items_product_id_location",
        "inventory_items",
        ["product_id", "location"],
        unique=False,
    )
    op.create_index(
        "ix_sales_order_items_product_id",
        "sales_order_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_sales_orders_status_created_at",
        "sales_orders",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_marketplace_listings_product_id",
        "marketplace_listings",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketplace_listings_marketplace_external",
        "marketplace_listings",
        ["marketplace_id", "external_listing_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_marketplace_listings_marketplace_external",
        table_name="marketplace_listings",
    )
    op.drop_index("ix_marketplace_listings_product_id", table_name="marketplace_listings")
    op.drop_index("ix_sales_orders_status_created_at", table_name="sales_orders")
    op.drop_index("ix_sales_order_items_product_id", table_name="sales_order_items")
    op.drop_index("ix_inventory_items_product_id_location", table_name="inventory_items")
