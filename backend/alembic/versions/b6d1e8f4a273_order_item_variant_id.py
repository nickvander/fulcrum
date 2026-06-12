"""sales_order_items.variant_id — variant granularity on order lines (FP-D)

Order-create has accepted ``variant_id`` per line since FP-04 (it drives
authoritative pricing AND the variant-aware atomic stock decrement), but the
line item never persisted WHICH variant sold — order reads degraded to the
product. This adds a nullable FK so the storefront can render the variant on
order history and so returns/exchanges can be variant-accurate.

SET NULL (not CASCADE) on variant delete: ``product_variants`` rows
CASCADE-delete their inventory, but an order line is sales history and must
survive the variant's removal (the line then reads like a legacy
product-level row).

Builds linearly on ``a9f3c2e7d105``. Additive — legacy rows stay NULL.

Revision ID: b6d1e8f4a273
Revises: a9f3c2e7d105
Create Date: 2026-06-11 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6d1e8f4a273"
down_revision: Union[str, Sequence[str], None] = "a9f3c2e7d105"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales_order_items", sa.Column("variant_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_sales_order_items_variant_id"),
        "sales_order_items",
        ["variant_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_sales_order_items_variant_id",
        "sales_order_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sales_order_items_variant_id", "sales_order_items", type_="foreignkey"
    )
    op.drop_index(op.f("ix_sales_order_items_variant_id"), table_name="sales_order_items")
    op.drop_column("sales_order_items", "variant_id")
