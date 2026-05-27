"""sales_order_returns table

Marketplaces issue refunds (ML payment-only refunds, Amazon partial
refunds, full-order cancellations) but they rarely tell us when a
physical product came back. Today there's no way to record "the
buyer returned 2 of 3 units; credit them back to inventory".

This table fills the gap. Each row is one operator-recorded return
event: which order it belongs to, which line item, how many units,
the reason note, and the actor who recorded it. The service layer
that creates these rows also calls
`InventoryService.adjust_stock(+qty, reason_code='return')` so the
inventory audit picks the return up automatically — the operator
gets one workflow that updates both the order's return history AND
their on-hand counts.

Schema notes:
  - `order_id` is required (a return is always against a known
    order; we don't support free-floating returns).
  - `order_item_id` is optional because some legacy orders have
    `SalesOrderItem.product_id IS NULL` (we didn't map them at
    ingest time), but the operator still needs to record the
    physical return. When NULL, `product_id` alone identifies what
    came back.
  - `quantity` is always positive (an explicit `1 unit returned`
    event); the stock credit is `+quantity` and the cost-engine
    breakdown for the parent order doesn't change — returns are
    physical, not financial.
  - `recorded_by_user_id` is a FK to the users table for the audit
    trail.

Revision ID: b3e9f2c5a740
Revises: a1d7e3c4b829
Create Date: 2026-05-20 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b3e9f2c5a740"
down_revision: Union[str, Sequence[str], None] = "a1d7e3c4b829"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales_order_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("sales_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # NULL allowed for legacy orders whose line items don't map
        # cleanly to a SalesOrderItem row — the operator still gets
        # to record the return against the product directly.
        sa.Column(
            "order_item_id",
            sa.Integer(),
            sa.ForeignKey("sales_order_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_sales_order_returns_quantity_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sales_order_returns_order_id"),
        "sales_order_returns",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_order_returns_received_at"),
        "sales_order_returns",
        ["received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_sales_order_returns_received_at"),
        table_name="sales_order_returns",
    )
    op.drop_index(
        op.f("ix_sales_order_returns_order_id"),
        table_name="sales_order_returns",
    )
    op.drop_table("sales_order_returns")
