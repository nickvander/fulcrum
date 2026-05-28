"""Coverage for GET /reports/returns-summary — per-channel physical
return rollup feeding the dashboard returns widget.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem, SalesOrderReturn
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


_COUNTER = {"n": 0}


def _seed_return(
    db: Session,
    *,
    source: OrderSource,
    sku: str,
    cost_price: float,
    quantity: int,
    when: datetime | None = None,
) -> int:
    """Insert a product + a paid order + a single return event for it.
    Returns the order id."""
    _COUNTER["n"] += 1
    suffix = _COUNTER["n"]
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"R {sku}-{suffix}", sku=f"{sku}-{suffix}",
            default_resale_price=cost_price * 2, cost_price=cost_price,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
    order = SalesOrder(
        status="PAID",
        total_price=cost_price * quantity * 2,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=source,
        external_order_id=f"RET-SUM-{suffix}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=quantity, price_per_unit=cost_price * 2,
        cost_per_unit=cost_price,
    ))
    db.commit()
    db.refresh(order)
    db.add(SalesOrderReturn(
        order_id=order.id, product_id=product.id, quantity=quantity,
        received_at=when or datetime.utcnow(),
        recorded_by_user_id=None,
        reason="seed", notes=None,
    ))
    db.commit()
    return order.id


def test_summary_rolls_up_by_channel(client: TestClient, db, admin_headers):
    """One ML return + one Amazon return → two channel rows + a
    totals row that sums them."""
    _seed_return(db, source=OrderSource.MERCADOLIBRE, sku="ML", cost_price=20.0, quantity=2)
    _seed_return(db, source=OrderSource.AMAZON, sku="AMZN", cost_price=15.0, quantity=1)

    resp = client.get("/api/v1/reports/returns-summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    by_channel = {r["source"]: r for r in body["by_channel"]}
    assert by_channel["MERCADOLIBRE"]["returns_count"] == 1
    assert by_channel["MERCADOLIBRE"]["units_returned"] == 2
    assert by_channel["MERCADOLIBRE"]["value_at_cost_mxn"] == pytest.approx(40.0)
    assert by_channel["AMAZON"]["returns_count"] == 1
    assert by_channel["AMAZON"]["units_returned"] == 1
    assert by_channel["AMAZON"]["value_at_cost_mxn"] == pytest.approx(15.0)

    totals = body["totals"]
    assert totals["source"] == "ALL"
    assert totals["returns_count"] == 2
    assert totals["units_returned"] == 3
    assert totals["value_at_cost_mxn"] == pytest.approx(55.0)


def test_summary_sorts_channels_by_value_desc(
    client: TestClient, db, admin_headers,
):
    """The bigger-capital channel lands first so the operator's eye
    naturally goes to the biggest returns exposure."""
    _seed_return(db, source=OrderSource.MERCADOLIBRE, sku="SMALL", cost_price=2.0, quantity=1)
    _seed_return(db, source=OrderSource.AMAZON, sku="BIG", cost_price=200.0, quantity=5)

    resp = client.get("/api/v1/reports/returns-summary", headers=admin_headers)
    rows = resp.json()["by_channel"]
    assert rows[0]["source"] == "AMAZON"
    assert rows[1]["source"] == "MERCADOLIBRE"


def test_summary_excludes_returns_outside_window(
    client: TestClient, db, admin_headers,
):
    """A 90-day-old return isn't in the 30d window."""
    long_ago = datetime.utcnow() - timedelta(days=90)
    _seed_return(
        db, source=OrderSource.MERCADOLIBRE, sku="OLD", cost_price=10.0, quantity=1,
        when=long_ago,
    )

    resp = client.get("/api/v1/reports/returns-summary", headers=admin_headers)
    assert resp.json()["totals"]["returns_count"] == 0
    assert resp.json()["by_channel"] == []


def test_summary_explicit_range_overrides_window_days(
    client: TestClient, db, admin_headers,
):
    long_ago = datetime.utcnow() - timedelta(days=120)
    _seed_return(
        db, source=OrderSource.MERCADOLIBRE, sku="ANCIENT", cost_price=10.0,
        quantity=1, when=long_ago,
    )

    short = client.get("/api/v1/reports/returns-summary", headers=admin_headers)
    assert short.json()["totals"]["returns_count"] == 0

    long = client.get(
        "/api/v1/reports/returns-summary",
        params={
            "start_date": (datetime.utcnow() - timedelta(days=150)).date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat(),
        },
        headers=admin_headers,
    )
    assert long.json()["totals"]["returns_count"] == 1


def test_summary_empty_envelope_when_nothing_returned(
    client: TestClient, admin_headers,
):
    resp = client.get("/api/v1/reports/returns-summary", headers=admin_headers)
    body = resp.json()
    assert body["by_channel"] == []
    assert body["totals"]["returns_count"] == 0
    assert body["totals"]["units_returned"] == 0


def test_summary_rejects_inverted_range(client: TestClient, admin_headers):
    resp = client.get(
        "/api/v1/reports/returns-summary",
        params={"start_date": "2026-04-01", "end_date": "2026-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.reports.invalidDateRange"
