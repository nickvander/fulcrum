"""Coverage for GET /reports/returns-list — paginated per-event
returns drill-down feeding the /reports/returns frontend page.

Shape mirrors `/refunds-list` so both pages can share a UI pattern.
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
    reason: str = "damaged",
    notes: str | None = None,
) -> int:
    """Insert a product + order + a single return event. Returns the
    return row's id so tests can assert ordering."""
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
        external_order_id=f"RET-LIST-{suffix}",
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
    ret = SalesOrderReturn(
        order_id=order.id, product_id=product.id, quantity=quantity,
        received_at=when or datetime.utcnow(),
        recorded_by_user_id=None,
        reason=reason, notes=notes,
    )
    db.add(ret)
    db.commit()
    db.refresh(ret)
    return ret.id


def test_returns_list_renders_envelope(client: TestClient, db, admin_headers):
    """Happy path: one return → one item + total=1 + window_label."""
    _seed_return(
        db, source=OrderSource.MERCADOLIBRE, sku="A", cost_price=10.0, quantity=2,
        reason="broken seal",
    )
    resp = client.get("/api/v1/reports/returns-list", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    row = body["items"][0]
    assert row["source"] == "MERCADOLIBRE"
    assert row["quantity"] == 2
    assert row["reason"] == "broken seal"
    assert row["value_at_cost"] == pytest.approx(20.0)
    assert row["product_sku"]
    assert row["product_name"]
    assert "window_label" in body


def test_returns_list_orders_newest_first(client: TestClient, db, admin_headers):
    """received_at desc is the operator's expected reading order."""
    older = datetime.utcnow() - timedelta(days=3)
    newer = datetime.utcnow() - timedelta(hours=1)
    _seed_return(db, source=OrderSource.AMAZON, sku="OLD", cost_price=5.0, quantity=1, when=older)
    _seed_return(db, source=OrderSource.AMAZON, sku="NEW", cost_price=5.0, quantity=1, when=newer)

    resp = client.get("/api/v1/reports/returns-list", headers=admin_headers)
    items = resp.json()["items"]
    assert items[0]["product_sku"].startswith("NEW-")
    assert items[1]["product_sku"].startswith("OLD-")


def test_returns_list_excludes_outside_window(client: TestClient, db, admin_headers):
    """A 90-day-old return doesn't appear in the 30d default."""
    _seed_return(
        db, source=OrderSource.MERCADOLIBRE, sku="OLD", cost_price=5.0, quantity=1,
        when=datetime.utcnow() - timedelta(days=90),
    )
    resp = client.get("/api/v1/reports/returns-list", headers=admin_headers)
    assert resp.json()["total"] == 0


def test_returns_list_source_filter(client: TestClient, db, admin_headers):
    """`source=AMAZON` drops non-Amazon rows."""
    _seed_return(db, source=OrderSource.MERCADOLIBRE, sku="ML", cost_price=5.0, quantity=1)
    _seed_return(db, source=OrderSource.AMAZON, sku="AMZN", cost_price=5.0, quantity=1)
    resp = client.get(
        "/api/v1/reports/returns-list",
        headers=admin_headers,
        params={"source": "amazon"},
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["source"] == "AMAZON"


def test_returns_list_rejects_unknown_source(client: TestClient, db, admin_headers):
    """A bogus source 400s with a localizable code rather than
    silently returning zero rows."""
    resp = client.get(
        "/api/v1/reports/returns-list",
        headers=admin_headers,
        params={"source": "nonsense"},
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "apiErrors.report.unknownSource"


def test_returns_list_paginates(client: TestClient, db, admin_headers):
    """skip/limit chops the response window; total stays the unfiltered
    count so the UI can render N–M of Total."""
    for i in range(5):
        _seed_return(
            db, source=OrderSource.FULCRUM, sku=f"P{i}", cost_price=1.0, quantity=1,
        )
    resp = client.get(
        "/api/v1/reports/returns-list",
        headers=admin_headers,
        params={"limit": 2, "skip": 0},
    )
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    resp2 = client.get(
        "/api/v1/reports/returns-list",
        headers=admin_headers,
        params={"limit": 2, "skip": 4},
    )
    body2 = resp2.json()
    assert body2["total"] == 5
    assert len(body2["items"]) == 1
