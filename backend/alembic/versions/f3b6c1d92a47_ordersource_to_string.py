"""sales_orders.source: native enum -> string (catalog-governed)

`SalesOrder.source` was a native Postgres enum (`ordersource`), so
adding a marketplace meant an `ALTER TYPE ... ADD VALUE` migration in
lockstep with the catalog. This converts the column to a plain varchar
whose valid values are governed by `marketplace_catalog.order_sources()`
— adding a marketplace is now a catalog entry with no DB change.

The cast preserves existing values verbatim (the enum labels were
already the strings FULCRUM / MERCADOLIBRE / AMAZON). The now-unused
`ordersource` enum type is dropped.

Revision ID: f3b6c1d92a47
Revises: e7c2f4a9d318
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa


revision = 'f3b6c1d92a47'
down_revision = 'e7c2f4a9d318'
branch_labels = None
depends_on = None


def upgrade():
    # enum -> varchar, preserving the label text. USING casts each enum
    # value to its text form.
    op.execute(
        "ALTER TABLE sales_orders "
        "ALTER COLUMN source TYPE VARCHAR USING source::text"
    )
    op.create_index('ix_sales_orders_source', 'sales_orders', ['source'])
    # Drop the now-orphaned enum type so it doesn't linger.
    op.execute("DROP TYPE IF EXISTS ordersource")


def downgrade():
    # Recreate the enum and cast back. Any out-of-enum values (e.g. a
    # marketplace added after this migration) would fail the cast — that
    # is the intended signal that you can't downgrade past a new channel.
    op.drop_index('ix_sales_orders_source', table_name='sales_orders')
    ordersource = sa.Enum('FULCRUM', 'MERCADOLIBRE', 'AMAZON', name='ordersource')
    ordersource.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE sales_orders "
        "ALTER COLUMN source TYPE ordersource USING source::ordersource"
    )
