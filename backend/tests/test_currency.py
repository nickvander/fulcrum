"""Coverage for the multi-currency foundation:

  - services/currency_service.py  (record / get / convert, historical)
  - GET  /currency/rates
  - POST /currency/rates
  - GET  /currency/convert
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.exchange_rate import ExchangeRate
from src.services import currency_service


pytestmark = pytest.mark.db


# --------------------------------------------------------------------------- #
# Service: record_rate
# --------------------------------------------------------------------------- #


def test_record_rate_inserts_then_upserts(db: Session):
    d = date(2026, 1, 10)
    currency_service.record_rate(
        db, base_currency="usd", quote_currency="mxn", rate=17.0, rate_date=d,
    )
    db.commit()
    rows = db.query(ExchangeRate).filter(ExchangeRate.base_currency == "USD").all()
    assert len(rows) == 1
    assert rows[0].rate == 17.0
    assert rows[0].quote_currency == "MXN"  # normalized upper-case

    # Re-recording the same pair+day updates in place, not a 2nd row.
    currency_service.record_rate(
        db, base_currency="USD", quote_currency="MXN", rate=17.5, rate_date=d,
    )
    db.commit()
    rows = db.query(ExchangeRate).filter(ExchangeRate.base_currency == "USD").all()
    assert len(rows) == 1
    assert rows[0].rate == 17.5


def test_record_rate_rejects_same_currency_and_nonpositive(db: Session):
    with pytest.raises(ValueError):
        currency_service.record_rate(db, base_currency="USD", quote_currency="USD", rate=1.0)
    with pytest.raises(ValueError):
        currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=0)


# --------------------------------------------------------------------------- #
# Service: get_rate (historical "on-or-before")
# --------------------------------------------------------------------------- #


def test_get_rate_picks_most_recent_on_or_before(db: Session):
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=17.0, rate_date=date(2026, 1, 1))
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=18.0, rate_date=date(2026, 2, 1))
    db.commit()

    # As-of mid-January → the Jan 1 rate (most recent on-or-before).
    r = currency_service.get_rate(db, base_currency="USD", quote_currency="MXN", on_date=date(2026, 1, 15))
    assert r is not None
    assert r.rate == 17.0

    # As-of March → the Feb 1 rate.
    r = currency_service.get_rate(db, base_currency="USD", quote_currency="MXN", on_date=date(2026, 3, 1))
    assert r.rate == 18.0

    # Before any recorded rate → None.
    r = currency_service.get_rate(db, base_currency="USD", quote_currency="MXN", on_date=date(2025, 12, 1))
    assert r is None


def test_get_rate_inverse_pair_fallback(db: Session):
    # Only USD→MXN recorded; MXN→USD should synthesize the inverse.
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=20.0, rate_date=date(2026, 1, 1))
    db.commit()
    r = currency_service.get_rate(db, base_currency="MXN", quote_currency="USD", on_date=date(2026, 1, 2))
    assert r is not None
    assert r.rate == pytest.approx(0.05)  # 1 / 20
    assert r.source.startswith("inverse:")


# --------------------------------------------------------------------------- #
# Service: convert
# --------------------------------------------------------------------------- #


def test_convert_same_currency_is_identity(db: Session):
    res = currency_service.convert(db, amount=100.0, base_currency="MXN", quote_currency="MXN")
    assert res.amount == 100.0
    assert res.rate == 1.0
    assert res.is_estimate is False


def test_convert_uses_historical_rate(db: Session):
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=17.0, rate_date=date(2026, 1, 1))
    db.commit()
    res = currency_service.convert(
        db, amount=10.0, base_currency="USD", quote_currency="MXN", on_date=date(2026, 1, 5),
    )
    assert res.amount == pytest.approx(170.0)
    assert res.rate == 17.0
    assert res.is_estimate is False
    assert res.rate_date == date(2026, 1, 1)


def test_convert_missing_rate_flags_estimate(db: Session):
    res = currency_service.convert(
        db, amount=10.0, base_currency="USD", quote_currency="MXN", on_date=date(2026, 1, 5),
    )
    # No rate on file → unconverted, flagged estimate so the UI can mark it.
    assert res.amount == 10.0
    assert res.rate == 1.0
    assert res.is_estimate is True


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


def test_post_rate_requires_admin_and_persists(client: TestClient, db, admin_headers):
    resp = client.post(
        "/api/v1/currency/rates",
        headers=admin_headers,
        json={"base_currency": "usd", "quote_currency": "mxn", "rate": 17.25, "rate_date": "2026-01-10"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["base_currency"] == "USD"
    assert body["quote_currency"] == "MXN"
    assert body["rate"] == 17.25


def test_post_rate_rejects_same_currency(client: TestClient, admin_headers):
    resp = client.post(
        "/api/v1/currency/rates",
        headers=admin_headers,
        json={"base_currency": "USD", "quote_currency": "USD", "rate": 1.0},
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "apiErrors.currency.invalidRate"


def test_list_rates_filters_by_pair(client: TestClient, db, admin_headers):
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=17.0, rate_date=date(2026, 1, 1))
    currency_service.record_rate(db, base_currency="EUR", quote_currency="MXN", rate=19.0, rate_date=date(2026, 1, 1))
    db.commit()
    resp = client.get("/api/v1/currency/rates", headers=admin_headers, params={"base_currency": "usd"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["base_currency"] == "USD"


def test_convert_endpoint_uses_recorded_rate(client: TestClient, db, admin_headers):
    currency_service.record_rate(db, base_currency="USD", quote_currency="MXN", rate=17.0, rate_date=date(2026, 1, 1))
    db.commit()
    resp = client.get(
        "/api/v1/currency/convert",
        headers=admin_headers,
        params={"amount": 10, "from": "USD", "to": "MXN", "on": "2026-01-05"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount"] == pytest.approx(170.0)
    assert body["rate"] == 17.0
    assert body["is_estimate"] is False
