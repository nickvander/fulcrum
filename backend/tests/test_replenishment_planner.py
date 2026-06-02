"""Tests for the replenishment-to-Full planner (B4).

Covers the date math, the internal-stock cap on transfer suggestions, the
no-velocity skip, and the HTTP contract of `GET /reports/replenishment`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.stock_transfer import LOCATION_INTERNAL, LOCATION_ML_FULL
from src.models.supplier_product import SupplierProduct
from src.schemas.product import ProductCreate
from src.services import replenishment_service


pytestmark = pytest.mark.db

# A fixed "today" so date arithmetic is deterministic.
TODAY = date(2026, 6, 1)


def _make_product(db, sku: str, *, reorder_quantity=None):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Repl {sku}", sku=sku,
            default_resale_price=100.0, cost_price=40.0,
            reorder_quantity=reorder_quantity,
        ),
    )


def _seed_ml_sales(db, product, units: int, *, window_days: int = 30):
    """Seed `units` of realized ML sales spread inside the window so the
    velocity comes out to roughly units/window_days/day."""
    order = SalesOrder(
        status="COMPLETED", total_price=units * 100.0, currency="MXN",
        created_at=datetime.utcnow() - timedelta(days=window_days // 2),
        source=OrderSource.MERCADOLIBRE.value,
        external_order_id=f"ML-{product.sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=units, price_per_unit=100.0, cost_per_unit=40.0,
    ))
    db.commit()


def _set_stock(db, product, *, location, qty):
    db.add(InventoryItem(product_id=product.id, location=location, quantity=qty))
    db.commit()


def test_skips_skus_with_no_ml_velocity(db):
    """A SKU with stock but no ML sales is omitted — nothing depletes Full."""
    p = _make_product(db, "REPL-NOVEL")
    _set_stock(db, p, location=LOCATION_ML_FULL, qty=5)

    report = replenishment_service.build_replenishment_plan(db, today=TODAY)

    assert all(r.product_id != p.id for r in report.rows)


def test_out_of_full_is_critical(db):
    """Selling on ML with zero Full stock => critical, send now."""
    p = _make_product(db, "REPL-CRIT")
    _seed_ml_sales(db, p, units=30)  # ~1/day
    _set_stock(db, p, location=LOCATION_INTERNAL, qty=100)
    # No ML-Full stock at all.

    report = replenishment_service.build_replenishment_plan(db, today=TODAY)

    row = next(r for r in report.rows if r.product_id == p.id)
    assert row.severity == "critical"
    assert row.full_available == 0
    # Send today, capped by internal on-hand (100).
    assert row.send_to_full_by == TODAY
    assert 0 < row.send_to_full_qty <= 100


def test_transfer_qty_capped_at_internal_on_hand(db):
    """Suggested send-to-Full never exceeds what's in the internal warehouse."""
    p = _make_product(db, "REPL-CAP")
    _seed_ml_sales(db, p, units=60)  # ~2/day -> large target need
    _set_stock(db, p, location=LOCATION_INTERNAL, qty=7)
    # Full is empty, so need is large but internal only has 7.

    report = replenishment_service.build_replenishment_plan(db, today=TODAY)

    row = next(r for r in report.rows if r.product_id == p.id)
    assert row.send_to_full_qty == 7


def test_send_by_date_lead_time_offset(db):
    """With comfortable Full cover, send-by is in the future: roughly
    (days of Full cover − Full-transfer lead)."""
    p = _make_product(db, "REPL-FUT")
    _seed_ml_sales(db, p, units=30)  # ~1/day
    _set_stock(db, p, location=LOCATION_ML_FULL, qty=40)   # ~40 days cover
    _set_stock(db, p, location=LOCATION_INTERNAL, qty=100)

    report = replenishment_service.build_replenishment_plan(
        db, today=TODAY, full_transfer_lead_days=14, target_cover_days=30,
    )

    row = next(r for r in report.rows if r.product_id == p.id)
    # ~40 days cover − 14 day lead => send ~26 days out (allow rounding slack).
    assert row.send_to_full_by is not None
    delta = (row.send_to_full_by - TODAY).days
    assert 24 <= delta <= 28


def test_reorder_uses_supplier_lead_time(db):
    """Reorder-by date is pulled earlier by a long supplier lead time."""
    supplier_p = _make_product(db, "REPL-SUP")
    _seed_ml_sales(db, supplier_p, units=30)  # ~1/day
    _set_stock(db, supplier_p, location=LOCATION_INTERNAL, qty=20)
    _set_stock(db, supplier_p, location=LOCATION_ML_FULL, qty=20)
    db.add(SupplierProduct(
        product_id=supplier_p.id, supplier_id=_a_supplier_id(db),
        lead_time_days=25,
    ))
    db.commit()

    report = replenishment_service.build_replenishment_plan(db, today=TODAY)

    row = next(r for r in report.rows if r.product_id == supplier_p.id)
    assert row.supplier_lead_time_days == 25
    assert row.reorder_by is not None
    assert row.reorder_qty > 0


def test_reorder_qty_honors_product_reorder_quantity(db):
    """When `reorder_quantity` is set, it is used verbatim as the reorder qty."""
    p = _make_product(db, "REPL-RQ", reorder_quantity=42)
    _seed_ml_sales(db, p, units=30)
    # Empty everywhere -> reorder need is positive.

    report = replenishment_service.build_replenishment_plan(db, today=TODAY)

    row = next(r for r in report.rows if r.product_id == p.id)
    assert row.reorder_qty == 42


def test_endpoint_contract(client: TestClient, db, admin_headers):
    p = _make_product(db, "REPL-API")
    _seed_ml_sales(db, p, units=30)
    _set_stock(db, p, location=LOCATION_INTERNAL, qty=50)

    resp = client.get(
        "/api/v1/reports/replenishment?velocity_window_days=30"
        "&full_transfer_lead_days=14&target_cover_days=30",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["velocity_window_days"] == 30
    assert body["full_transfer_lead_days"] == 14
    assert body["target_cover_days"] == 30
    assert any(r["product_id"] == p.id for r in body["rows"])


def test_endpoint_requires_auth(client: TestClient):
    resp = client.get("/api/v1/reports/replenishment")
    assert resp.status_code == 401


def _a_supplier_id(db) -> int:
    """Create (once) a throwaway supplier and return its id."""
    from src.models.supplier import Supplier

    sup = db.query(Supplier).first()
    if sup is None:
        sup = Supplier(name="Repl Test Supplier")
        db.add(sup)
        db.commit()
        db.refresh(sup)
    return sup.id
