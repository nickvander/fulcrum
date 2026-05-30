"""
CurrencyService — record FX rates and convert amounts between
currencies using the rate that applied on a given date.

Design notes
------------
- Rates are stored as `1 base = rate quote` in the `exchange_rates`
  table, one row per (base, quote, day).
- Conversions are *historical*: `convert(amount, USD, MXN, on=2026-01-15)`
  uses the most-recent USD→MXN rate recorded on or before 2026-01-15,
  so a purchase keeps the rate that was true when it happened rather
  than drifting with today's market.
- Same-currency conversions short-circuit to rate 1.0.
- If no rate is on file the conversion is flagged `is_estimate=True`
  with rate 1.0 — the caller decides whether to surface "≈" / a
  warning rather than silently presenting a wrong number.
- Currency codes are normalized to upper-case ISO 4217 strings.

This is deliberately feed-agnostic: rates can be entered manually by
the operator or upserted by a future Banxico/ECB worker — the
conversion path is identical.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.models.exchange_rate import ExchangeRate


@dataclass
class ConversionResult:
    """Outcome of a single conversion."""
    amount: float            # converted amount, rounded to 2dp
    rate: float              # rate applied (1 base = rate quote)
    base_currency: str
    quote_currency: str
    rate_date: Optional[date]  # the date of the rate actually used
    is_estimate: bool        # True when no rate was on file (rate=1.0)


def _norm(code: str) -> str:
    return (code or "").strip().upper()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def record_rate(
    db: Session,
    *,
    base_currency: str,
    quote_currency: str,
    rate: float,
    rate_date: Optional[date] = None,
    source: str = "manual",
) -> ExchangeRate:
    """Upsert a rate for (base, quote, day). Re-recording the same day
    overwrites the prior value (e.g. operator corrects a typo)."""
    base = _norm(base_currency)
    quote = _norm(quote_currency)
    if base == quote:
        raise ValueError("base_currency and quote_currency must differ")
    if rate <= 0:
        raise ValueError("rate must be positive")
    on = rate_date or _today()

    existing = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
            ExchangeRate.rate_date == on,
        )
        .first()
    )
    if existing:
        existing.rate = rate
        existing.source = source
        return existing

    row = ExchangeRate(
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        rate_date=on,
        source=source,
    )
    db.add(row)
    return row


def get_rate(
    db: Session,
    *,
    base_currency: str,
    quote_currency: str,
    on_date: Optional[date] = None,
) -> Optional[ExchangeRate]:
    """Return the most-recent rate on-or-before `on_date`, or None.

    Tries the direct pair first; if absent, tries the inverse pair and
    returns a synthetic in-memory ExchangeRate carrying 1/rate so a
    single recorded USD→MXN row also answers MXN→USD queries."""
    base = _norm(base_currency)
    quote = _norm(quote_currency)
    if base == quote:
        return None  # caller treats same-currency as rate 1.0
    on = on_date or _today()

    direct = (
        db.query(ExchangeRate)
        .filter(
            and_(
                ExchangeRate.base_currency == base,
                ExchangeRate.quote_currency == quote,
                ExchangeRate.rate_date <= on,
            )
        )
        .order_by(ExchangeRate.rate_date.desc())
        .first()
    )
    if direct:
        return direct

    inverse = (
        db.query(ExchangeRate)
        .filter(
            and_(
                ExchangeRate.base_currency == quote,
                ExchangeRate.quote_currency == base,
                ExchangeRate.rate_date <= on,
            )
        )
        .order_by(ExchangeRate.rate_date.desc())
        .first()
    )
    if inverse and inverse.rate:
        # Synthetic (not persisted) inverse rate.
        return ExchangeRate(
            base_currency=base,
            quote_currency=quote,
            rate=round(1.0 / inverse.rate, 8),
            rate_date=inverse.rate_date,
            source=f"inverse:{inverse.source}",
        )
    return None


def convert(
    db: Session,
    *,
    amount: float,
    base_currency: str,
    quote_currency: str,
    on_date: Optional[date] = None,
) -> ConversionResult:
    """Convert `amount` from base→quote using the historical rate.

    Same currency → identity (rate 1.0). No rate on file → identity
    with `is_estimate=True` so the caller can flag it."""
    base = _norm(base_currency)
    quote = _norm(quote_currency)

    if base == quote:
        return ConversionResult(
            amount=round(amount, 2), rate=1.0,
            base_currency=base, quote_currency=quote,
            rate_date=on_date, is_estimate=False,
        )

    row = get_rate(db, base_currency=base, quote_currency=quote, on_date=on_date)
    if row is None:
        return ConversionResult(
            amount=round(amount, 2), rate=1.0,
            base_currency=base, quote_currency=quote,
            rate_date=None, is_estimate=True,
        )

    return ConversionResult(
        amount=round(amount * row.rate, 2),
        rate=row.rate,
        base_currency=base,
        quote_currency=quote,
        rate_date=row.rate_date,
        is_estimate=False,
    )
