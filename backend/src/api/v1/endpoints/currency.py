"""Currency endpoints — record FX rates + convert amounts.

Mounted at `/api/v1/currency`.

  - GET  /currency/rates           list recorded rates (filterable)
  - POST /currency/rates           record/upsert a rate (admin)
  - GET  /currency/convert         convert an amount historically

Conversions delegate to `services/currency_service.py`, which owns the
"most-recent rate on-or-before date" logic + inverse-pair fallback.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api import dependencies
from src.core.errors import LocalizedHTTPException
from src.database import get_db
from src.models.exchange_rate import ExchangeRate
from src.models.user import User
from src.services import currency_service


router = APIRouter()


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class ExchangeRateRead(BaseModel):
    id: int
    base_currency: str
    quote_currency: str
    rate: float
    rate_date: date
    source: str

    model_config = {"from_attributes": True}


class ExchangeRateCreate(BaseModel):
    base_currency: str = Field(..., max_length=8)
    quote_currency: str = Field(..., max_length=8)
    rate: float = Field(..., gt=0)
    rate_date: Optional[date] = None
    source: str = Field("manual", max_length=32)


class ConversionRead(BaseModel):
    amount: float
    rate: float
    base_currency: str
    quote_currency: str
    rate_date: Optional[date]
    is_estimate: bool


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.get("/rates", response_model=List[ExchangeRateRead])
def list_rates(
    *,
    db: Session = Depends(get_db),
    base_currency: Optional[str] = Query(None),
    quote_currency: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """List recorded FX rates, newest first. Optional pair filter."""
    q = db.query(ExchangeRate)
    if base_currency:
        q = q.filter(ExchangeRate.base_currency == base_currency.strip().upper())
    if quote_currency:
        q = q.filter(ExchangeRate.quote_currency == quote_currency.strip().upper())
    return (
        q.order_by(ExchangeRate.rate_date.desc(), ExchangeRate.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/rates", response_model=ExchangeRateRead, status_code=201)
def create_rate(
    *,
    db: Session = Depends(get_db),
    payload: ExchangeRateCreate,
    current_user: User = Depends(dependencies.get_current_active_superuser),
):
    """Record (or update) a rate for a currency pair on a date.
    Admin-only — rates feed financial conversions."""
    try:
        row = currency_service.record_rate(
            db,
            base_currency=payload.base_currency,
            quote_currency=payload.quote_currency,
            rate=payload.rate,
            rate_date=payload.rate_date,
            source=payload.source,
        )
    except ValueError as exc:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.currency.invalidRate",
            params={"reason": str(exc)},
            detail=str(exc),
        )
    db.commit()
    db.refresh(row)
    return row


@router.get("/convert", response_model=ConversionRead)
def convert_amount(
    *,
    db: Session = Depends(get_db),
    amount: float = Query(...),
    from_currency: str = Query(..., alias="from"),
    to_currency: str = Query(..., alias="to"),
    on_date: Optional[date] = Query(None, alias="on"),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Convert `amount` from→to using the rate on-or-before `on`
    (defaults to today). `is_estimate=true` means no rate was on file
    and the amount is returned unconverted (rate 1.0)."""
    result = currency_service.convert(
        db,
        amount=amount,
        base_currency=from_currency,
        quote_currency=to_currency,
        on_date=on_date,
    )
    return ConversionRead(
        amount=result.amount,
        rate=result.rate,
        base_currency=result.base_currency,
        quote_currency=result.quote_currency,
        rate_date=result.rate_date,
        is_estimate=result.is_estimate,
    )
