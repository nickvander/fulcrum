"""inventory_count_sessions + inventory_count_session_items

Operator-facing workflow: do a physical count of stock across N
SKUs in one go, enter expected-vs-actual per SKU, commit the
deltas as a single batch of inventory adjustments tagged
`reason_code='recount'`. Without this table the operator's only
option is the one-at-a-time stock-adjustment dialog, which is the
biggest source of audit-log noise and clicks-per-count.

`inventory_count_sessions`:
  - One row per count session.
  - `status`: `in_progress` → `committed` | `cancelled`. Both
    terminal — a committed session writes adjustments; a cancelled
    session is a no-op record so the operator's "I started a count
    and abandoned it" history isn't silently lost.
  - `location` defaults to `"default"` (single-warehouse case).
    Multi-location workspaces scope the count to one location at a
    time so a SKU stocked in two warehouses doesn't get
    double-counted.

`inventory_count_session_items`:
  - One row per SKU in the session.
  - `expected_quantity` is snapshotted at add-time from the live
    `InventoryItem.quantity`. If stock moves between add and
    commit, the operator's count is still compared against what
    they saw on screen — same as a physical count form.
  - `counted_quantity` starts NULL; the operator enters it as
    they tally. Commit ignores NULL-counted rows (operator
    skipped the SKU; no adjustment).
  - Unique on `(session_id, product_id, variant_id)` — adding the
    same SKU twice is a 409 from the endpoint.

Revision ID: c5d1e8a3b072
Revises: b3e9f2c5a740
Create Date: 2026-05-20 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c5d1e8a3b072"
down_revision: Union[str, Sequence[str], None] = "b3e9f2c5a740"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUSES = ("in_progress", "committed", "cancelled")


def upgrade() -> None:
    op.create_table(
        "inventory_count_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="in_progress"),
        sa.Column("location", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "started_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('" + "','".join(_STATUSES) + "')",
            name="ck_inventory_count_sessions_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_count_sessions_status"),
        "inventory_count_sessions",
        ["status"],
        unique=False,
    )

    op.create_table(
        "inventory_count_session_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("inventory_count_sessions.id", ondelete="CASCADE"),
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
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        # NULL until the operator enters a count; commit skips NULLs.
        sa.Column("counted_quantity", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "product_id", "variant_id",
            name="uq_inventory_count_session_items_sku",
        ),
    )
    op.create_index(
        op.f("ix_inventory_count_session_items_session_id"),
        "inventory_count_session_items",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inventory_count_session_items_session_id"),
        table_name="inventory_count_session_items",
    )
    op.drop_table("inventory_count_session_items")
    op.drop_index(
        op.f("ix_inventory_count_sessions_status"),
        table_name="inventory_count_sessions",
    )
    op.drop_table("inventory_count_sessions")
