"""add_supplier_product_aliases

Revision ID: 2b7f0c8d9e12
Revises: c6eac61d94b2
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7f0c8d9e12"
down_revision: Union[str, Sequence[str], None] = "c6eac61d94b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier_product_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("alias_sku", sa.String(), nullable=True),
        sa.Column("alias_name", sa.String(), nullable=True),
        sa.Column("normalized_sku", sa.String(), nullable=True),
        sa.Column("normalized_name", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("match_count", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "normalized_name", name="uq_supplier_alias_name"),
        sa.UniqueConstraint("supplier_id", "normalized_sku", name="uq_supplier_alias_sku"),
    )
    op.create_index(op.f("ix_supplier_product_aliases_id"), "supplier_product_aliases", ["id"], unique=False)
    op.create_index(
        op.f("ix_supplier_product_aliases_is_active"),
        "supplier_product_aliases",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_aliases_normalized_name"),
        "supplier_product_aliases",
        ["normalized_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_aliases_normalized_sku"),
        "supplier_product_aliases",
        ["normalized_sku"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_aliases_product_id"),
        "supplier_product_aliases",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_aliases_supplier_id"),
        "supplier_product_aliases",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_product_aliases_variant_id"),
        "supplier_product_aliases",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_product_aliases_variant_id"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_supplier_id"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_product_id"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_normalized_sku"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_normalized_name"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_is_active"), table_name="supplier_product_aliases")
    op.drop_index(op.f("ix_supplier_product_aliases_id"), table_name="supplier_product_aliases")
    op.drop_table("supplier_product_aliases")
