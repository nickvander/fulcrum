"""
End-to-end tests for `GET /api/v1/reports/profit-summary`.

This is the "¿Gané o perdí?" surface — the ONLY endpoint that subtracts
operating expenses from order-contribution profit to produce the business
bottom line. Tests cover:
  - profit = contribution − operating_expenses math
  - period → window resolution and start/end/window_days consistency
  - operating expenses subtracted over the same span
  - empty-orders flag (no fake $0 verdict)
  - verdict thresholds (won / lost / even)
  - the double-count warning flag
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.crud.crud_expense import expense as crud_expense
from src.models.marketplace import Marketplace
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.expense import ExpenseCreate
from src.schemas.product import ProductCreate
from src.services.order_cost_engine import upsert_breakdown


pytestmark = pytest.mark.db


def _ensure_ml(db):
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.0  # keep fees out so the math is exact in tests
    mp.default_shipping_cost = 0.0
    db.commit()
    db.refresh(mp)
    return mp


def _seed_order(db, *, total, sku, qty, price, cost, status="COMPLETED"):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Profit {sku}", sku=sku,
            default_resale_price=price, cost_price=cost,
        ),
    )
    order = SalesOrder(
        status=status, total_price=total, currency="MXN",
        created_at=datetime.utcnow(), source=OrderSource.MERCADOLIBRE,
        external_order_id=f"EXT-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=price, cost_per_unit=cost,
    ))
    db.commit()
    upsert_breakdown(db, order)
    db.commit()
    return order


def _add_expense(db, *, amount, category="Rent", on=None):
    crud_expense.create(db, obj_in=ExpenseCreate(
        description=f"{category} expense",
        amount=amount,
        category=category,
        date=on or date.today(),
    ))


def test_profit_is_contribution_minus_expenses(client: TestClient, db, admin_headers):
    """Revenue 500, COGS 100 → contribution 400. Subtract 150 of operating
    expenses → bottom line 250, verdict 'won'."""
    _ensure_ml(db)
    _seed_order(db, total=500.0, sku="PS-WIN", qty=1, price=500.0, cost=100.0)
    _add_expense(db, amount=150.0, category="Rent")

    r = client.get(
        "/api/v1/reports/profit-summary?period=this_month", headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["revenue_amount_mxn"] == 500.0
    assert body["sales_costs_amount"] == 100.0
    assert body["contribution_profit_amount"] == 400.0
    assert body["operating_expenses_amount"] == 150.0
    assert body["bottom_line_amount"] == 250.0
    assert body["verdict"] == "won"
    assert body["has_realized_orders"] is True
    assert body["orders"] == 1


def test_expenses_can_flip_profit_to_loss(client: TestClient, db, admin_headers):
    """Contribution 400 but 600 of expenses → bottom line -200, verdict
    'lost'. Confirms expenses are actually subtracted."""
    _ensure_ml(db)
    _seed_order(db, total=500.0, sku="PS-LOSE", qty=1, price=500.0, cost=100.0)
    _add_expense(db, amount=600.0, category="Rent")

    body = client.get(
        "/api/v1/reports/profit-summary?period=this_month", headers=admin_headers,
    ).json()
    assert body["contribution_profit_amount"] == 400.0
    assert body["operating_expenses_amount"] == 600.0
    assert body["bottom_line_amount"] == -200.0
    assert body["verdict"] == "lost"


def test_verdict_even_at_exact_zero(client: TestClient, db, admin_headers):
    """Contribution exactly equals expenses → bottom line 0 → 'even'."""
    _ensure_ml(db)
    _seed_order(db, total=300.0, sku="PS-EVEN", qty=1, price=300.0, cost=100.0)
    _add_expense(db, amount=200.0, category="Rent")  # contribution 200

    body = client.get(
        "/api/v1/reports/profit-summary?period=this_month", headers=admin_headers,
    ).json()
    assert body["contribution_profit_amount"] == 200.0
    assert body["operating_expenses_amount"] == 200.0
    assert body["bottom_line_amount"] == 0.0
    assert body["verdict"] == "even"


def test_empty_orders_returns_flag_not_fake_zero(client: TestClient, db, admin_headers):
    """No realized orders → has_realized_orders False and verdict null, even
    if expenses exist. The UI must show an empty state, NOT 'quedaste a
    mano'."""
    _ensure_ml(db)
    _add_expense(db, amount=99.0, category="Rent")

    body = client.get(
        "/api/v1/reports/profit-summary?period=this_month", headers=admin_headers,
    ).json()
    assert body["orders"] == 0
    assert body["has_realized_orders"] is False
    assert body["verdict"] is None
    assert body["revenue_amount_mxn"] == 0.0


def test_period_window_alignment(client: TestClient, db, admin_headers):
    """start/end/window_days are mutually consistent: end == today, and the
    rolling window_days span covers [start, end]."""
    _ensure_ml(db)
    _seed_order(db, total=100.0, sku="PS-ALIGN", qty=1, price=100.0, cost=10.0)

    for period in ("this_month", "last_7d", "last_30d"):
        body = client.get(
            f"/api/v1/reports/profit-summary?period={period}", headers=admin_headers,
        ).json()
        start = date.fromisoformat(body["start"])
        end = date.fromisoformat(body["end"])
        assert end == date.today()
        assert start <= end
        # window_days, applied as a rolling [now - window_days, now] window,
        # must reach back to at least `start` (same span coverage).
        assert end - timedelta(days=body["window_days"]) <= start
        if period == "last_7d":
            assert body["window_days"] == 7
        elif period == "last_30d":
            assert body["window_days"] == 30


def test_double_count_warning_present(client: TestClient, db, admin_headers):
    """v1 subtracts the full expense total and warns about possible
    ad/shipping double counting; excluded_categories is empty (plumbing
    off)."""
    _ensure_ml(db)
    _seed_order(db, total=100.0, sku="PS-DC", qty=1, price=100.0, cost=10.0)

    body = client.get(
        "/api/v1/reports/profit-summary?period=this_month", headers=admin_headers,
    ).json()
    assert body["double_count_warning"] is True
    assert body["excluded_categories"] == []


def test_invalid_period_rejected(client: TestClient, db, admin_headers):
    r = client.get(
        "/api/v1/reports/profit-summary?period=this_year", headers=admin_headers,
    )
    assert r.status_code in (400, 422)


def test_profit_summary_requires_auth(client: TestClient):
    r = client.get("/api/v1/reports/profit-summary")
    assert r.status_code == 401
