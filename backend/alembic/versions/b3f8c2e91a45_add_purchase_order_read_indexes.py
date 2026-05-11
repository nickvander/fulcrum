"""add_purchase_order_read_indexes

Revision ID: b3f8c2e91a45
Revises: 8a7c2d4f9b31
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3f8c2e91a45"
down_revision: Union[str, Sequence[str], None] = "8a7c2d4f9b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_purchase_order_items_po_id",
        "purchase_order_items",
        ["po_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_order_items_product_id",
        "purchase_order_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_orders_created_at_id",
        "purchase_orders",
        ["created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_purchase_orders_created_at_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_order_items_product_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_po_id", table_name="purchase_order_items")
