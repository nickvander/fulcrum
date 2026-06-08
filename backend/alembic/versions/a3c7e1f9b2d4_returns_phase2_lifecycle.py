"""Returns Phase 2: return status lifecycle + order customer ownership

Adds the customer self-service returns surface's storage:

* ``sales_orders.customer_user_id`` — the storefront customer who placed the
  order, the ownership anchor for ``/customers/me/orders/{id}`` (NULL for
  marketplace orders and pre-existing rows).
* ``sales_order_returns`` lifecycle columns — ``status`` (requested→approved→
  received→refunded / rejected, default ``requested``), ``requested_by_user_id``
  (customer, vs the operator ``recorded_by_user_id``), ``amount`` (refund amount,
  Float MXN), ``refund_reference`` + ``refunded_at``, a unique
  ``idempotency_key`` (customer request path), and ``stock_recredited_at`` (the
  credit-once guard).

Additive; all nullable / server-default-safe so existing rows and the BFF's
service key are unaffected. Builds linearly on the sole head ``f2b3c4d5e6a7``.

Revision ID: a3c7e1f9b2d4
Revises: f2b3c4d5e6a7
Create Date: 2026-06-08 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3c7e1f9b2d4"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- sales_orders: ownership anchor ---
    op.add_column(
        "sales_orders",
        sa.Column("customer_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sales_orders_customer_user_id_users",
        "sales_orders",
        "users",
        ["customer_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sales_orders_customer_user_id",
        "sales_orders",
        ["customer_user_id"],
    )

    # --- sales_order_returns: lifecycle ---
    op.add_column(
        "sales_order_returns",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="requested",
        ),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("amount", sa.Float(), nullable=True),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("refund_reference", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "sales_order_returns",
        sa.Column("stock_recredited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sales_order_returns_requested_by_user_id_users",
        "sales_order_returns",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sales_order_returns_idempotency_key",
        "sales_order_returns",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sales_order_returns_idempotency_key",
        table_name="sales_order_returns",
    )
    op.drop_constraint(
        "fk_sales_order_returns_requested_by_user_id_users",
        "sales_order_returns",
        type_="foreignkey",
    )
    op.drop_column("sales_order_returns", "stock_recredited_at")
    op.drop_column("sales_order_returns", "idempotency_key")
    op.drop_column("sales_order_returns", "refunded_at")
    op.drop_column("sales_order_returns", "refund_reference")
    op.drop_column("sales_order_returns", "amount")
    op.drop_column("sales_order_returns", "requested_by_user_id")
    op.drop_column("sales_order_returns", "status")

    op.drop_index(
        "ix_sales_orders_customer_user_id", table_name="sales_orders"
    )
    op.drop_constraint(
        "fk_sales_orders_customer_user_id_users",
        "sales_orders",
        type_="foreignkey",
    )
    op.drop_column("sales_orders", "customer_user_id")
