"""MX-grade addresses + durable ship-to on orders (FP-B)

Two additive changes for the storefront checkout:

* ``addresses`` gains ``colonia`` / ``interior`` / ``recipient_name`` /
  ``phone`` — the Mexican-address granularity (neighborhood + unit) carriers
  need, plus recipient identity so a saved address is a self-sufficient
  ship-to for prefill.
* ``sales_orders`` gains nullable ``ship_to_*`` columns so the destination a
  storefront order ships to is persisted durably on the system of record —
  previously it lived only in the BFF's TTL-bound checkout snapshot and the
  carrier's systems. NULL on POS / marketplace / legacy orders.

Builds linearly on the sole head ``d5c0de100001``. Additive — no backfill.
These columns are PII and are never logged.

Revision ID: a9f3c2e7d105
Revises: d5c0de100001
Create Date: 2026-06-11 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9f3c2e7d105"
down_revision: Union[str, Sequence[str], None] = "d5c0de100001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("addresses", sa.Column("colonia", sa.String(length=128), nullable=True))
    op.add_column("addresses", sa.Column("interior", sa.String(length=32), nullable=True))
    op.add_column(
        "addresses", sa.Column("recipient_name", sa.String(length=128), nullable=True)
    )
    op.add_column("addresses", sa.Column("phone", sa.String(length=20), nullable=True))

    op.add_column("sales_orders", sa.Column("ship_to_name", sa.String(length=128), nullable=True))
    op.add_column(
        "sales_orders", sa.Column("ship_to_street", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "sales_orders", sa.Column("ship_to_colonia", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "sales_orders", sa.Column("ship_to_interior", sa.String(length=32), nullable=True)
    )
    op.add_column("sales_orders", sa.Column("ship_to_city", sa.String(length=128), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_state", sa.String(length=64), nullable=True))
    op.add_column(
        "sales_orders", sa.Column("ship_to_postal_code", sa.String(length=10), nullable=True)
    )
    op.add_column(
        "sales_orders", sa.Column("ship_to_country", sa.String(length=64), nullable=True)
    )
    op.add_column("sales_orders", sa.Column("ship_to_phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "ship_to_phone")
    op.drop_column("sales_orders", "ship_to_country")
    op.drop_column("sales_orders", "ship_to_postal_code")
    op.drop_column("sales_orders", "ship_to_state")
    op.drop_column("sales_orders", "ship_to_city")
    op.drop_column("sales_orders", "ship_to_interior")
    op.drop_column("sales_orders", "ship_to_colonia")
    op.drop_column("sales_orders", "ship_to_street")
    op.drop_column("sales_orders", "ship_to_name")

    op.drop_column("addresses", "phone")
    op.drop_column("addresses", "recipient_name")
    op.drop_column("addresses", "interior")
    op.drop_column("addresses", "colonia")
