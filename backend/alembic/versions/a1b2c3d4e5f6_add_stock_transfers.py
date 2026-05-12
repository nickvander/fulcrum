"""add_stock_transfers

Revision ID: a1b2c3d4e5f6
Revises: 7f3b9c2d1a44
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "7f3b9c2d1a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_location", sa.String(), nullable=False, server_default="default"),
        sa.Column("dest_location", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("external_inbound_id", sa.String(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_stock_transfers_status",
        "stock_transfers",
        ["status"],
    )
    op.create_index(
        "ix_stock_transfers_created_at",
        "stock_transfers",
        ["created_at"],
    )

    op.create_table(
        "stock_transfer_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "transfer_id",
            sa.Integer(),
            sa.ForeignKey("stock_transfers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "variant_id",
            sa.Integer(),
            sa.ForeignKey("product_variants.id"),
            nullable=True,
        ),
        sa.Column("qty_planned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_shipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_received", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_stock_transfer_items_transfer_id",
        "stock_transfer_items",
        ["transfer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_transfer_items_transfer_id", table_name="stock_transfer_items")
    op.drop_table("stock_transfer_items")
    op.drop_index("ix_stock_transfers_created_at", table_name="stock_transfers")
    op.drop_index("ix_stock_transfers_status", table_name="stock_transfers")
    op.drop_table("stock_transfers")
