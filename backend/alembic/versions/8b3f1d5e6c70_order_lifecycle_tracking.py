"""order lifecycle tracking: status-event audit + reversed_at + stock re-credit

Surfaces marketplace-side cancellations and refunds as first-class
data so the operator can answer "how many orders did we refund last
week?" instead of staring at a `SalesOrder.status` column that gets
silently overwritten on every poll.

Three additions land together because they share one
status-transition hook in the ingestion paths:

  - `sales_order_status_events` — append-only audit. Every time an
    ingestion path observes `existing.status != new.status` it writes
    one row. Lets the refunds dashboard query history (today the
    pollers just overwrite the column, so we have no history).
    Source signal column captures which ingestion path wrote the
    event (`ml_webhook`, `ml_poll`, `amazon_poll`, `manual`) — handy
    for diagnosing "the poll keeps undoing the webhook" type bugs.

  - `order_cost_breakdowns.reversed_at` — set automatically when the
    parent order leaves the realized-status set. The cost-engine
    rollups filter on `reversed_at IS NULL` so a reversed order
    disappears from current-period totals while staying queryable
    by the refunds widget. Reversal is orthogonal to `fees_source`
    so we keep it as its own column rather than overloading the
    enum.

  - `sales_orders.stock_recredited_at` — idempotency marker for the
    cancel-before-ship stock re-credit. Set when the lifecycle
    service credits inventory back; non-NULL means "already done,
    skip on subsequent polls".

  - `amazon_order_refunds` — captures Amazon's `RefundEventList`
    rows from the SP-API Finances payload. The settlement worker
    already parses these for fee-netting purposes; this table
    persists the refund amounts themselves so the refunds widget
    can surface partial-refund cases where the order's top-level
    `OrderStatus` stays `Shipped` (e.g. buyer returned one line
    item out of three). Keyed on
    `(order_id, amazon_refund_id)` for idempotency — re-polling
    the same financial-events payload can't double-count.

Revision ID: 8b3f1d5e6c70
Revises: 7c2e8d4a91f6
Create Date: 2026-05-19 04:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8b3f1d5e6c70"
down_revision: Union[str, Sequence[str], None] = "7c2e8d4a91f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales_order_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("sales_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # NULL `from_status` represents the very first event for an
        # order (insert path). Subsequent events always carry both
        # bounds.
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_signal", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sales_order_status_events_order_id"),
        "sales_order_status_events",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_order_status_events_changed_at"),
        "sales_order_status_events",
        ["changed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sales_order_status_events_to_status"),
        "sales_order_status_events",
        ["to_status"],
        unique=False,
    )

    op.add_column(
        "order_cost_breakdowns",
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_order_cost_breakdowns_reversed_at"),
        "order_cost_breakdowns",
        ["reversed_at"],
        unique=False,
    )

    op.add_column(
        "sales_orders",
        sa.Column("stock_recredited_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "amazon_order_refunds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("sales_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SP-API's identifier for the refund / chargeback / adjustment
        # event. NOT the AmazonOrderId — the FinancialEvents payload
        # uses a separate `AmazonOrderId` per event row + a posted
        # timestamp; we synthesize a stable key per event from the
        # posted-date + event index.
        sa.Column("amazon_refund_id", sa.String(length=128), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="MXN"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "amazon_refund_id", name="uq_amazon_refunds_event"),
    )
    op.create_index(
        op.f("ix_amazon_order_refunds_order_id"),
        "amazon_order_refunds",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_amazon_order_refunds_posted_at"),
        "amazon_order_refunds",
        ["posted_at"],
        unique=False,
    )

    # Widen the alert_rules CHECK constraint to accept the new
    # `refund_rate_spike` type. The original constraint was added by
    # migration 6e0a4c5d2f19 with the three v1 types hard-coded; we
    # drop and recreate with the full set.
    op.drop_constraint("ck_alert_rules_type", "alert_rules", type_="check")
    op.create_check_constraint(
        "ck_alert_rules_type",
        "alert_rules",
        "alert_type IN ('low_margin','sales_dip','stockout_risk','refund_rate_spike')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_alert_rules_type", "alert_rules", type_="check")
    op.create_check_constraint(
        "ck_alert_rules_type",
        "alert_rules",
        "alert_type IN ('low_margin','sales_dip','stockout_risk')",
    )
    op.drop_index(
        op.f("ix_amazon_order_refunds_posted_at"),
        table_name="amazon_order_refunds",
    )
    op.drop_index(
        op.f("ix_amazon_order_refunds_order_id"),
        table_name="amazon_order_refunds",
    )
    op.drop_table("amazon_order_refunds")
    op.drop_column("sales_orders", "stock_recredited_at")
    op.drop_index(
        op.f("ix_order_cost_breakdowns_reversed_at"),
        table_name="order_cost_breakdowns",
    )
    op.drop_column("order_cost_breakdowns", "reversed_at")
    op.drop_index(
        op.f("ix_sales_order_status_events_to_status"),
        table_name="sales_order_status_events",
    )
    op.drop_index(
        op.f("ix_sales_order_status_events_changed_at"),
        table_name="sales_order_status_events",
    )
    op.drop_index(
        op.f("ix_sales_order_status_events_order_id"),
        table_name="sales_order_status_events",
    )
    op.drop_table("sales_order_status_events")
