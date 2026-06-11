"""Add storefront discount codes (FP Phase 1): discount_codes + redemptions

Two new tables plus two additive columns on sales_orders. Fulcrum is the system
of record for money + orders + CFDI, so promo codes are defined, validated, and
applied here. `discount_codes` holds the rule; `discount_redemptions` is the
usage ledger (atomic global + per-customer limits). `sales_orders` gains
`discount_code_id` (FK SET NULL) + `discount_amount` (Float, default 0); the
order's `total_price` is the post-discount total.

Builds linearly on the sole head ``c5e9a3b7f1d2``. Additive — no data backfill.

Revision ID: d5c0de100001
Revises: c5e9a3b7f1d2
Create Date: 2026-06-10 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5c0de100001"
down_revision: Union[str, Sequence[str], None] = "c5e9a3b7f1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="percentage"),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("min_spend", sa.Float(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("per_customer_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discount_codes_id"), "discount_codes", ["id"], unique=False)
    op.create_index(op.f("ix_discount_codes_code"), "discount_codes", ["code"], unique=True)

    op.create_table(
        "discount_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discount_code_id", sa.Integer(), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), nullable=False),
        sa.Column("customer_user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["discount_code_id"], ["discount_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discount_redemptions_id"), "discount_redemptions", ["id"], unique=False)
    op.create_index(
        op.f("ix_discount_redemptions_discount_code_id"),
        "discount_redemptions",
        ["discount_code_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discount_redemptions_sales_order_id"),
        "discount_redemptions",
        ["sales_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discount_redemptions_customer_user_id"),
        "discount_redemptions",
        ["customer_user_id"],
        unique=False,
    )

    op.add_column(
        "sales_orders",
        sa.Column("discount_code_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index(
        op.f("ix_sales_orders_discount_code_id"), "sales_orders", ["discount_code_id"], unique=False
    )
    op.create_foreign_key(
        "fk_sales_orders_discount_code_id",
        "sales_orders",
        "discount_codes",
        ["discount_code_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sales_orders_discount_code_id", "sales_orders", type_="foreignkey")
    op.drop_index(op.f("ix_sales_orders_discount_code_id"), table_name="sales_orders")
    op.drop_column("sales_orders", "discount_amount")
    op.drop_column("sales_orders", "discount_code_id")

    op.drop_table("discount_redemptions")
    op.drop_table("discount_codes")
