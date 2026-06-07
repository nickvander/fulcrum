"""stock reservations (OXXO/SPEI pending-payment holds)

Adds `stock_reservations` + `stock_reservation_items` so the storefront BFF can
hold stock during an async (OXXO/SPEI) pending-payment window. Reserving
decrements on-hand (audited as a SALE tagged source=stock_reservation);
releasing credits it back; consuming at order-create links the order without a
second decrement. No existing tables/constraints are altered (the audit
reason-code CHECK is untouched — reservations reuse SALE/CANCELLATION).

Builds linearly on the sole head `a7c2e9d4b6f1` (category taxonomy).

Revision ID: d8b3f1a52c47
Revises: a7c2e9d4b6f1
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8b3f1a52c47"
down_revision: Union[str, Sequence[str], None] = "a7c2e9d4b6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reservation_key", sa.String(length=128), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="active"
        ),
        sa.Column(
            "location", sa.String(length=64), nullable=False, server_default="default"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("sales_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_stock_reservations_reservation_key",
        "stock_reservations",
        ["reservation_key"],
        unique=True,
    )
    op.create_index("ix_stock_reservations_status", "stock_reservations", ["status"])
    op.create_index(
        "ix_stock_reservations_expires_at", "stock_reservations", ["expires_at"]
    )
    op.create_index(
        "ix_stock_reservations_order_id", "stock_reservations", ["order_id"]
    )

    op.create_table(
        "stock_reservation_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reservation_id",
            sa.Integer(),
            sa.ForeignKey("stock_reservations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            sa.ForeignKey("product_variants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_stock_reservation_items_reservation_id",
        "stock_reservation_items",
        ["reservation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_reservation_items_reservation_id",
        table_name="stock_reservation_items",
    )
    op.drop_table("stock_reservation_items")

    op.drop_index("ix_stock_reservations_order_id", table_name="stock_reservations")
    op.drop_index("ix_stock_reservations_expires_at", table_name="stock_reservations")
    op.drop_index("ix_stock_reservations_status", table_name="stock_reservations")
    op.drop_index(
        "ix_stock_reservations_reservation_key", table_name="stock_reservations"
    )
    op.drop_table("stock_reservations")
