"""
End-to-end coverage for GET /api/v1/reports/dead-stock.

"Dead stock" = products with on-hand inventory but near-zero
recent sales velocity. The endpoint powers the dashboard's
dead-stock widget; this file pins the contract behaviors that
widget depends on (ordering, threshold filtering, never-sold
products bubbling to the top, bundle exclusion, capital-at-risk
tie-breaker).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.schemas.product import ProductCreate


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(db, sku, *, on_hand=10, cost=5.0, is_bundle=False, **overrides):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Dead {sku}", sku=sku,
            default_resale_price=50.0, cost_price=cost,
            is_bundle=is_bundle,
            **overrides,
        ),
    )
    if on_hand > 0:
        db.add(InventoryItem(
            product_id=product.id, quantity=on_hand, location="default",
        ))
        db.commit()
    return product


def _sell_units(
    db, product, *, qty, days_ago=0, status="COMPLETED",
):
    """Add an order line for `qty` units of `product` dated
    `days_ago` calendar days back."""
    order = SalesOrder(
        status=status,
        total_price=qty * 50.0,
        currency="MXN",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
        source=OrderSource.MERCADOLIBRE,
        external_order_id=f"DS-{product.sku}-{days_ago}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=50.0, cost_per_unit=float(product.cost_price or 0),
    ))
    db.commit()
    return order


# ---------------------------------------------------------------------------
# Filtering rules
# ---------------------------------------------------------------------------


def test_returns_only_products_with_on_hand_stock(
    client: TestClient, db, admin_headers,
):
    """A product with zero on-hand is OUT of stock, not dead stock —
    the stockout report covers that case. This endpoint must skip
    zero-stock rows even if they have no recent velocity."""
    _make_product(db, "DS-ZERO-STOCK", on_hand=0)
    stocked = _make_product(db, "DS-STOCKED", on_hand=5)

    response = client.get("/api/v1/reports/dead-stock", headers=admin_headers)
    body = response.json()
    skus = [r["product_sku"] for r in body["rows"]]
    assert "DS-ZERO-STOCK" not in skus
    assert "DS-STOCKED" in skus
    assert stocked.id in [r["product_id"] for r in body["rows"]]


def test_filters_out_products_above_velocity_threshold(
    client: TestClient, db, admin_headers,
):
    """A product moving briskly is healthy, not dead — must be
    excluded. Threshold default 0.1 units/day → over 30d a product
    selling > 3 units in the window is excluded."""
    healthy = _make_product(db, "DS-HEALTHY", on_hand=5)
    _sell_units(db, healthy, qty=10, days_ago=2)  # 10 units in 30d → 0.33/day > 0.1

    dead = _make_product(db, "DS-DEAD", on_hand=5)
    _sell_units(db, dead, qty=1, days_ago=90)  # No sales in the window → 0/day

    response = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    )
    body = response.json()
    skus = [r["product_sku"] for r in body["rows"]]
    assert "DS-HEALTHY" not in skus
    assert "DS-DEAD" in skus


def test_threshold_query_param_changes_the_set(
    client: TestClient, db, admin_headers,
):
    """A higher threshold pulls in more rows (more SKUs count as
    "dead-ish"). Operator dials this per channel."""
    slow = _make_product(db, "DS-SLOW", on_hand=5)
    _sell_units(db, slow, qty=3, days_ago=10)  # 3/30 = 0.1/day exactly

    # Default threshold 0.1 → slow is at the boundary (<=), included.
    body_default = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    ).json()
    assert "DS-SLOW" in [r["product_sku"] for r in body_default["rows"]]

    # Threshold of 0.05 — slow's 0.1 exceeds it → excluded.
    body_tight = client.get(
        "/api/v1/reports/dead-stock?window_days=30&threshold_daily_velocity=0.05",
        headers=admin_headers,
    ).json()
    assert "DS-SLOW" not in [r["product_sku"] for r in body_tight["rows"]]


def test_excludes_bundle_products(client: TestClient, db, admin_headers):
    """Bundles have virtual stock (computed from components). They'd
    show up as zero-velocity dead stock here when the operator
    actually cares about the component-level dead stock. Skip them
    — same rule the velocity/margin reports already follow."""
    _make_product(db, "DS-BUNDLE", on_hand=3, is_bundle=True)
    _make_product(db, "DS-NOT-BUNDLE", on_hand=3)

    body = client.get("/api/v1/reports/dead-stock", headers=admin_headers).json()
    skus = [r["product_sku"] for r in body["rows"]]
    assert "DS-BUNDLE" not in skus
    assert "DS-NOT-BUNDLE" in skus


# ---------------------------------------------------------------------------
# Per-row math + metadata
# ---------------------------------------------------------------------------


def test_row_computes_velocity_and_units_sold(
    client: TestClient, db, admin_headers,
):
    """A SKU with 1 unit sold in 30 days → velocity 0.0333/day, still
    under the default 0.1 threshold so it appears. Verify the math
    + units_sold pass through."""
    slow = _make_product(db, "DS-SLOW-MATH", on_hand=10)
    _sell_units(db, slow, qty=1, days_ago=10)

    body = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    ).json()
    row = next(r for r in body["rows"] if r["product_sku"] == "DS-SLOW-MATH")
    assert row["units_sold"] == 1
    assert row["daily_velocity"] == pytest.approx(1.0 / 30.0, abs=1e-4)


def test_never_sold_product_shows_null_days_since_last_sale(
    client: TestClient, db, admin_headers,
):
    """A product with stock but zero sales ever → days_since_last_sale
    is None (not a misleading "0 days" or "today")."""
    never = _make_product(db, "DS-NEVER", on_hand=5)
    body = client.get("/api/v1/reports/dead-stock", headers=admin_headers).json()
    row = next(r for r in body["rows"] if r["product_sku"] == "DS-NEVER")
    assert row["days_since_last_sale"] is None
    assert never.id == row["product_id"]


def test_days_since_last_sale_reflects_real_age_outside_the_window(
    client: TestClient, db, admin_headers,
):
    """A SKU last sold 90 days ago in a 30-day window: velocity is
    0/day (no sales IN the window), but days_since_last_sale is 90 —
    not None and not 30. The last-sale lookup spans all history."""
    old = _make_product(db, "DS-OLD", on_hand=5)
    _sell_units(db, old, qty=2, days_ago=90)

    body = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    ).json()
    row = next(r for r in body["rows"] if r["product_sku"] == "DS-OLD")
    assert row["units_sold"] == 0
    assert row["daily_velocity"] == 0
    assert row["days_since_last_sale"] == 90


def test_stock_value_uses_current_cost_price(
    client: TestClient, db, admin_headers,
):
    """Stock value = on_hand × cost_price. Operator triages by
    capital at risk, not just unit count."""
    valuable = _make_product(db, "DS-VAL", on_hand=10, cost=25.0)
    body = client.get("/api/v1/reports/dead-stock", headers=admin_headers).json()
    row = next(r for r in body["rows"] if r["product_sku"] == "DS-VAL")
    assert row["cost_price"] == 25.0
    assert row["stock_value_at_cost"] == 250.0
    assert valuable.id == row["product_id"]


# ---------------------------------------------------------------------------
# Ordering rules — the contract the operator UI depends on
# ---------------------------------------------------------------------------


def test_never_sold_products_sort_to_the_top(
    client: TestClient, db, admin_headers,
):
    """Never-sold inventory is "infinitely dead" — operator's eye
    should land there first. Even a 365-day-old single sale beats
    never-sold for ordering position."""
    never = _make_product(db, "DS-SORT-NEVER", on_hand=5)
    sold_long_ago = _make_product(db, "DS-SORT-OLD", on_hand=5)
    _sell_units(db, sold_long_ago, qty=1, days_ago=365)

    body = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    ).json()
    skus = [r["product_sku"] for r in body["rows"]]
    never_idx = skus.index("DS-SORT-NEVER")
    old_idx = skus.index("DS-SORT-OLD")
    assert never_idx < old_idx
    assert never.id != sold_long_ago.id


def test_older_last_sale_sorts_higher_among_already_sold_products(
    client: TestClient, db, admin_headers,
):
    """Among two SKUs that have both sold but are now dead, the
    one with the older last_sale_at sorts first — operator wants
    the longest-dead at the top."""
    sixty = _make_product(db, "DS-SORT-60", on_hand=5)
    _sell_units(db, sixty, qty=1, days_ago=60)

    thirty = _make_product(db, "DS-SORT-30", on_hand=5)
    _sell_units(db, thirty, qty=1, days_ago=31)  # outside 30d window

    body = client.get(
        "/api/v1/reports/dead-stock?window_days=30", headers=admin_headers,
    ).json()
    skus = [r["product_sku"] for r in body["rows"]]
    assert skus.index("DS-SORT-60") < skus.index("DS-SORT-30")


def test_capital_at_risk_breaks_ties_in_last_sale_age(
    client: TestClient, db, admin_headers,
):
    """Two never-sold SKUs → tied on days_since_last_sale (None).
    The higher stock_value_at_cost wins the tiebreaker so the
    operator sees the bigger capital risk first."""
    cheap = _make_product(db, "DS-TIE-CHEAP", on_hand=10, cost=1.0)  # $10 frozen
    pricey = _make_product(db, "DS-TIE-PRICEY", on_hand=2, cost=100.0)  # $200 frozen

    body = client.get(
        "/api/v1/reports/dead-stock", headers=admin_headers,
    ).json()
    skus = [r["product_sku"] for r in body["rows"]]
    assert skus.index("DS-TIE-PRICEY") < skus.index("DS-TIE-CHEAP")
    assert cheap.id != pricey.id


# ---------------------------------------------------------------------------
# Limit + auth
# ---------------------------------------------------------------------------


def test_limit_query_param_caps_result_rows(
    client: TestClient, db, admin_headers,
):
    for i in range(7):
        _make_product(db, f"DS-LIMIT-{i}", on_hand=3)
    body = client.get(
        "/api/v1/reports/dead-stock?limit=3", headers=admin_headers,
    ).json()
    assert len(body["rows"]) == 3


def test_endpoint_returns_thresholds_in_response_envelope(
    client: TestClient, db, admin_headers,
):
    """The frontend renders "Daily velocity <= X over last N days"
    in the widget header. It reads those from the response so the
    constants aren't duplicated in the UI."""
    body = client.get(
        "/api/v1/reports/dead-stock?window_days=14&threshold_daily_velocity=0.2",
        headers=admin_headers,
    ).json()
    assert body["window_days"] == 14
    assert body["threshold_daily_velocity"] == 0.2


def test_endpoint_requires_auth(client: TestClient):
    response = client.get("/api/v1/reports/dead-stock")
    assert response.status_code == 401


def test_endpoint_returns_empty_when_no_inventory_exists(
    client: TestClient, db, admin_headers,
):
    """No products + no inventory → empty list, not a 5xx."""
    body = client.get(
        "/api/v1/reports/dead-stock", headers=admin_headers,
    ).json()
    assert body["rows"] == []
