"""Coverage for the paginated sales-orders list endpoint.

`GET /api/v1/sales-orders/` returns a `SalesOrderListResponse` envelope
`{items, total, skip, limit}` with:
  - `total` = filtered+searched count BEFORE skip/limit,
  - a case-insensitive substring `search` on `external_order_id`,
  - a `net_margin_percent` field per row (from the 1:1 OrderCostBreakdown,
    null when absent / zero-revenue), eager-loaded (no N+1),
  - the existing source/status/days filters, AND-composing with search,
  - stable `created_at desc, id desc` ordering and honored skip/limit.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.order import (
    OrderCostBreakdown,
    OrderSource,
    SalesOrder,
    SalesOrderItem,
)
from src.schemas.product import ProductCreate
from src.services import order_cost_engine


pytestmark = pytest.mark.db

_N = {"i": 0}

LIST_URL = "/api/v1/sales-orders/"


def _product(db: Session, *, cost: float, price: float):
    _N["i"] += 1
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"SOL {_N['i']}", sku=f"SOL-{_N['i']}",
            cost_price=cost, default_resale_price=price, currency="MXN",
        ),
    )


def _order(
    db: Session,
    *,
    source=OrderSource.MERCADOLIBRE,
    status="COMPLETED",
    external_order_id=None,
    when=None,
    with_breakdown=True,
    product=None,
    qty=2,
    price=200.0,
):
    _N["i"] += 1
    o = SalesOrder(
        status=status,
        total_price=qty * price,
        currency="MXN",
        created_at=when or datetime.utcnow(),
        source=source,
        external_order_id=external_order_id or f"EXT-{_N['i']}",
    )
    db.add(o)
    db.flush()
    if with_breakdown:
        if product is None:
            product = _product(db, cost=80.0, price=price)
        db.add(SalesOrderItem(
            order_id=o.id, product_id=product.id, quantity=qty,
            price_per_unit=price, cost_per_unit=product.cost_price,
        ))
        db.flush()
        db.refresh(o)
        order_cost_engine.upsert_breakdown(db, o)
    db.commit()
    db.refresh(o)
    return o


# --------------------------------------------------------------------------- #
# Envelope shape + pagination
# --------------------------------------------------------------------------- #


def test_list_returns_envelope_shape(client: TestClient, db, admin_headers):
    _order(db, external_order_id="EXT-AAA")
    body = client.get(LIST_URL, headers=admin_headers).json()
    assert set(body.keys()) == {"items", "total", "skip", "limit"}
    assert isinstance(body["items"], list)
    assert body["total"] >= 1
    assert body["skip"] == 0
    assert body["limit"] == 100


def test_total_is_count_before_paginate(client: TestClient, db, admin_headers):
    # Five orders in a fresh source so we can isolate them with a filter.
    for _ in range(5):
        _order(db, source=OrderSource.AMAZON)

    resp = client.get(
        LIST_URL, params={"source": "AMAZON", "limit": 2}, headers=admin_headers,
    )
    body = resp.json()
    # total reflects the full filtered set; the page is capped by limit.
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["limit"] == 2


def test_skip_limit_honored_and_page_two(client: TestClient, db, admin_headers):
    for _ in range(5):
        _order(db, source=OrderSource.FULCRUM)

    page1 = client.get(
        LIST_URL, params={"source": "FULCRUM", "limit": 2, "skip": 0},
        headers=admin_headers,
    ).json()
    page2 = client.get(
        LIST_URL, params={"source": "FULCRUM", "limit": 2, "skip": 2},
        headers=admin_headers,
    ).json()

    assert page1["total"] == page2["total"] == 5
    assert page2["skip"] == 2
    ids1 = {r["id"] for r in page1["items"]}
    ids2 = {r["id"] for r in page2["items"]}
    # Disjoint pages — no row appears twice across the window.
    assert ids1.isdisjoint(ids2)


def test_ordering_is_created_desc_then_id_desc(client: TestClient, db, admin_headers):
    base = datetime(2026, 1, 1, 12, 0, 0)
    older = _order(db, source=OrderSource.FULCRUM, when=base)
    newer = _order(db, source=OrderSource.FULCRUM, when=base + timedelta(days=1))

    items = client.get(
        LIST_URL, params={"source": "FULCRUM"}, headers=admin_headers,
    ).json()["items"]
    ids = [r["id"] for r in items]
    assert ids.index(newer.id) < ids.index(older.id)


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #


def test_search_matches_external_id_case_insensitive_partial(client, db, admin_headers):
    _order(db, source=OrderSource.AMAZON, external_order_id="ML-ABC123")
    _order(db, source=OrderSource.AMAZON, external_order_id="ML-XYZ999")

    # Lowercased + partial still matches the uppercase stored id.
    body = client.get(
        LIST_URL, params={"source": "AMAZON", "search": "abc"}, headers=admin_headers,
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["external_order_id"] == "ML-ABC123"


def test_search_blank_is_ignored(client: TestClient, db, admin_headers):
    _order(db, source=OrderSource.FULCRUM, external_order_id="KEEP-1")
    _order(db, source=OrderSource.FULCRUM, external_order_id="KEEP-2")

    body = client.get(
        LIST_URL, params={"source": "FULCRUM", "search": "   "}, headers=admin_headers,
    ).json()
    assert body["total"] == 2


def test_search_composes_with_source_filter(client: TestClient, db, admin_headers):
    _order(db, source=OrderSource.AMAZON, external_order_id="SHARED-1")
    _order(db, source=OrderSource.FULCRUM, external_order_id="SHARED-2")

    # Same substring, but the source filter narrows to one channel.
    body = client.get(
        LIST_URL,
        params={"source": "AMAZON", "search": "shared"},
        headers=admin_headers,
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["source"] == "AMAZON"


def test_search_no_match_returns_empty(client: TestClient, db, admin_headers):
    _order(db, source=OrderSource.AMAZON, external_order_id="REAL-1")
    body = client.get(
        LIST_URL, params={"search": "does-not-exist-zzz"}, headers=admin_headers,
    ).json()
    assert body["total"] == 0
    assert body["items"] == []


# --------------------------------------------------------------------------- #
# Margin field
# --------------------------------------------------------------------------- #


def test_margin_present_when_breakdown_exists(client: TestClient, db, admin_headers):
    o = _order(db, source=OrderSource.FULCRUM, with_breakdown=True)
    # Confirm the engine actually wrote a margin for this order.
    cb = db.query(OrderCostBreakdown).filter_by(order_id=o.id).one()
    assert cb.net_margin_percent is not None

    items = client.get(
        LIST_URL, params={"source": "FULCRUM"}, headers=admin_headers,
    ).json()["items"]
    row = next(r for r in items if r["id"] == o.id)
    assert row["net_margin_percent"] == pytest.approx(cb.net_margin_percent)


def test_margin_null_when_no_breakdown(client: TestClient, db, admin_headers):
    o = _order(db, source=OrderSource.FULCRUM, with_breakdown=False)
    items = client.get(
        LIST_URL, params={"source": "FULCRUM"}, headers=admin_headers,
    ).json()["items"]
    row = next(r for r in items if r["id"] == o.id)
    assert row["net_margin_percent"] is None
