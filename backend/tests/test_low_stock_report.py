"""
Tests for the /api/v1/reports/low-stock endpoint and the underlying
threshold-precedence logic (Product.reorder_point > ProductInventorySettings
> StoreSettings default).
"""
from datetime import datetime

import pytest

from src.crud import crud_product
from src.models.inventory import InventoryItem, InventoryAdjustment
from src.models.product_inventory_settings import ProductInventorySettings
from src.schemas.product import ProductCreate
from src.services.inventory_service import inventory_service


pytestmark = pytest.mark.db


def _make_product(db, sku, *, reorder_point=None, reorder_quantity=None):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Low {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
        ),
    )
    return product


def _seed_stock(db, product_id, qty, location="default"):
    if qty:
        inventory_service.adjust_stock(
            db=db,
            product_id=product_id,
            adjustment=qty,
            reason="seed",
            location=location,
        )
    else:
        # Make sure an InventoryItem row exists at zero so on_hand is queryable.
        existing = (
            db.query(InventoryItem)
            .filter(
                InventoryItem.product_id == product_id,
                InventoryItem.location == location,
            )
            .first()
        )
        if not existing:
            db.add(InventoryItem(product_id=product_id, quantity=0, location=location))
            db.add(
                InventoryAdjustment(
                    product_id=product_id,
                    adjustment=0,
                    reason="seed",
                    timestamp=datetime.utcnow(),
                    created_by="system",
                )
            )
    db.commit()


def test_low_stock_report_marks_zero_stock_as_critical(client, db, admin_headers):
    p = _make_product(db, "REP-CRIT")
    _seed_stock(db, p.id, 0)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    assert response.status_code == 200
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["severity"] == "critical"
    assert row["on_hand"] == 0


def test_low_stock_report_uses_product_reorder_point(client, db, admin_headers):
    """Product.reorder_point overrides product-settings + store default."""
    p = _make_product(db, "REP-ROP", reorder_point=50)
    _seed_stock(db, p.id, 40)  # under 50 -> "low"

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["threshold"] == 50
    assert row["severity"] == "low"
    assert row["reorder_point"] == 50


def test_low_stock_report_falls_back_to_product_inventory_settings(client, db, admin_headers):
    """When reorder_point is None, fall back to ProductInventorySettings."""
    p = _make_product(db, "REP-PIS")
    _seed_stock(db, p.id, 8)
    db.add(ProductInventorySettings(product_id=p.id, low_stock_quantity_threshold=20))
    db.commit()

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["threshold"] == 20
    assert row["severity"] == "low"


def test_low_stock_report_falls_back_to_store_default(client, db, admin_headers):
    """No product or settings override → falls back to store default (10)."""
    p = _make_product(db, "REP-DEFAULT")
    _seed_stock(db, p.id, 5)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["threshold"] == 10
    assert row["severity"] == "low"


def test_low_stock_report_excludes_well_stocked_products(client, db, admin_headers):
    p = _make_product(db, "REP-OK", reorder_point=5)
    _seed_stock(db, p.id, 100)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    assert all(r["product_id"] != p.id for r in rows)


def test_low_stock_report_watch_band(client, db, admin_headers):
    """Stock just above the threshold but within 25% buffer = "watch"."""
    p = _make_product(db, "REP-WATCH", reorder_point=10)
    _seed_stock(db, p.id, 12)  # 12 > 10 but <= 12.5 → watch band

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["severity"] == "watch"


def test_low_stock_report_uses_explicit_reorder_quantity(client, db, admin_headers):
    p = _make_product(db, "REP-RQ", reorder_point=10, reorder_quantity=42)
    _seed_stock(db, p.id, 0)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    assert row["suggested_reorder_qty"] == 42


def test_low_stock_report_falls_back_suggested_when_unset(client, db, admin_headers):
    """Without reorder_quantity, suggested = max(velocity*30, threshold*2)."""
    p = _make_product(db, "REP-SUGGEST", reorder_point=10)
    _seed_stock(db, p.id, 0)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    row = next(r for r in rows if r["product_id"] == p.id)
    # No sales velocity in test → suggested should be threshold * 2 = 20
    assert row["suggested_reorder_qty"] >= 20


def test_low_stock_report_summary_counts(client, db, admin_headers):
    pa = _make_product(db, "REP-S-CRIT", reorder_point=5)
    _seed_stock(db, pa.id, 0)
    pb = _make_product(db, "REP-S-LOW", reorder_point=5)
    _seed_stock(db, pb.id, 3)
    pc = _make_product(db, "REP-S-WATCH", reorder_point=10)
    _seed_stock(db, pc.id, 12)

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    body = response.json()
    assert body["total_critical"] >= 1
    assert body["total_low"] >= 1
    assert body["total_watch"] >= 1


def test_low_stock_report_orders_by_severity_then_days_left(client, db, admin_headers):
    pa = _make_product(db, "REP-ORDER-A", reorder_point=10)
    _seed_stock(db, pa.id, 0)  # critical
    pb = _make_product(db, "REP-ORDER-B", reorder_point=10)
    _seed_stock(db, pb.id, 5)  # low

    response = client.get("/api/v1/reports/low-stock", headers=admin_headers)
    rows = response.json()["rows"]
    sevs = [r["severity"] for r in rows if r["product_id"] in (pa.id, pb.id)]
    # The critical product must come before the low product.
    assert sevs.index("critical") < sevs.index("low")
