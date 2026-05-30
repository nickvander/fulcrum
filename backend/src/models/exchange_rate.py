"""
ExchangeRate — a dated FX rate between two currencies.

The point of storing rates *with a date* is historical accuracy: a
product sourced in USD and sold in MXN should be converted at the rate
that was true on the day of the transaction, not today's rate. So
conversions look up the most-recent rate on-or-before the relevant
date rather than a single live number.

`rate` is expressed as: 1 unit of `base_currency` = `rate` units of
`quote_currency`. e.g. base=USD, quote=MXN, rate=17.10 means
US$1 = MX$17.10.

Rates are recorded manually today (operator enters the day's rate, or
a future Banxico/exchange-feed worker upserts them). `source` records
where the number came from so a manual override is distinguishable
from a fed rate.
"""
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        # One rate per currency-pair per day. Re-recording the same day
        # updates in place (the service upserts on this key).
        UniqueConstraint(
            "base_currency", "quote_currency", "rate_date",
            name="uq_exchange_rate_pair_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # ISO 4217 codes, upper-cased by the service before persistence.
    base_currency = Column(String(8), nullable=False, index=True)
    quote_currency = Column(String(8), nullable=False, index=True)

    # 1 base = `rate` quote.
    rate = Column(Float, nullable=False)

    # The calendar day this rate applies to (UTC). Conversions pick the
    # most-recent rate on-or-before the transaction date.
    rate_date = Column(Date, nullable=False, index=True)

    # 'manual' | 'banxico' | 'ecb' | ... — provenance of the number.
    source = Column(String(32), nullable=False, default="manual")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
