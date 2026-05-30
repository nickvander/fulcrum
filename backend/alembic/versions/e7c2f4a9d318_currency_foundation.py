"""currency foundation: exchange_rates table + products.currency

Two coupled pieces of the multi-currency feature:

1. `products.currency` — the product's native pricing currency
   (ISO 4217). Defaults to MXN (the primary market). A product
   sourced/listed in USD carries 'USD' so its cost/price figures are
   unambiguous.

2. `exchange_rates` — dated FX rates (1 base = rate quote, one row per
   pair per day). Conversions look up the most-recent rate on-or-before
   the transaction date so historical purchases keep the rate that was
   true when they happened.

Revision ID: e7c2f4a9d318
Revises: d6f1a92c4b85
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7c2f4a9d318'
down_revision = 'd6f1a92c4b85'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'products',
        sa.Column(
            'currency', sa.String(length=8),
            nullable=False, server_default='MXN',
        ),
    )

    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_currency', sa.String(length=8), nullable=False),
        sa.Column('quote_currency', sa.String(length=8), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('rate_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'base_currency', 'quote_currency', 'rate_date',
            name='uq_exchange_rate_pair_date',
        ),
    )
    op.create_index('ix_exchange_rates_id', 'exchange_rates', ['id'])
    op.create_index('ix_exchange_rates_base_currency', 'exchange_rates', ['base_currency'])
    op.create_index('ix_exchange_rates_quote_currency', 'exchange_rates', ['quote_currency'])
    op.create_index('ix_exchange_rates_rate_date', 'exchange_rates', ['rate_date'])


def downgrade():
    op.drop_index('ix_exchange_rates_rate_date', table_name='exchange_rates')
    op.drop_index('ix_exchange_rates_quote_currency', table_name='exchange_rates')
    op.drop_index('ix_exchange_rates_base_currency', table_name='exchange_rates')
    op.drop_index('ix_exchange_rates_id', table_name='exchange_rates')
    op.drop_table('exchange_rates')
    op.drop_column('products', 'currency')
