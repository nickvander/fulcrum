"""Tests for the shopping-cart-style reorder endpoint added in this slice.

POST /api/v1/reports/low-stock/reorder takes a list of product_ids
(typically a selection from the low-stock widget) and creates one
DRAFT PurchaseOrder per primary supplier."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import models
from src.models.product import Product
from src.models.supplier import Supplier
from src.models.supplier_product import SupplierProduct
from src.models.purchase_order import PurchaseOrder


def _seed_product(db: Session, name: str, sku: str, cost: float = 5.0) -> Product:
    p = Product(name=name, sku=sku, default_resale_price=cost * 2, cost_price=cost, is_bundle=False)
    db.add(p)
    db.flush()
    return p


def _seed_supplier(db: Session, name: str) -> Supplier:
    s = Supplier(name=name)
    db.add(s)
    db.flush()
    return s


def _link(db: Session, product: Product, supplier: Supplier, cost: float = 4.0, primary: bool = True) -> SupplierProduct:
    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        cost_price=cost,
        is_primary=primary,
    )
    db.add(sp)
    db.flush()
    return sp


@pytest.mark.db
def test_reorder_groups_products_by_supplier_into_separate_pos(
    client: TestClient, admin_headers: dict, db: Session, test_admin_user: models.User
):
    s1 = _seed_supplier(db, "Acme Supplies")
    s2 = _seed_supplier(db, "Beta Wholesale")
    pA = _seed_product(db, "Widget A", "WID-A", cost=10.0)
    pB = _seed_product(db, "Widget B", "WID-B", cost=15.0)
    pC = _seed_product(db, "Widget C", "WID-C", cost=8.0)
    pA.reorder_quantity = 5
    pB.reorder_quantity = 10
    pC.reorder_quantity = 3
    _link(db, pA, s1, cost=9.0)
    _link(db, pB, s1, cost=14.0)
    _link(db, pC, s2, cost=7.5)
    db.commit()

    response = client.post(
        "/api/v1/reports/low-stock/reorder",
        headers=admin_headers,
        json={"product_ids": [pA.id, pB.id, pC.id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["created_purchase_orders"]) == 2
    assert body["skipped"] == []

    by_supplier = {po["supplier_id"]: po for po in body["created_purchase_orders"]}
    assert by_supplier[s1.id]["product_count"] == 2
    assert by_supplier[s1.id]["supplier_name"] == "Acme Supplies"
    assert by_supplier[s1.id]["total_amount"] == pytest.approx(185.0)

    assert by_supplier[s2.id]["product_count"] == 1
    assert by_supplier[s2.id]["supplier_name"] == "Beta Wholesale"
    assert by_supplier[s2.id]["total_amount"] == pytest.approx(22.5)

    persisted_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.id.in_([po["purchase_order_id"] for po in body["created_purchase_orders"]])
    ).all()
    assert len(persisted_pos) == 2
    for po in persisted_pos:
        assert po.status.lower() == "draft"
        assert po.notes == "Auto-created from low-stock reorder cart"


@pytest.mark.db
def test_reorder_uses_quantity_overrides_when_provided(
    client: TestClient, admin_headers: dict, db: Session
):
    s = _seed_supplier(db, "S1")
    p = _seed_product(db, "Override Test", "OVR-1", cost=10.0)
    p.reorder_quantity = 999
    _link(db, p, s, cost=10.0)
    db.commit()

    response = client.post(
        "/api/v1/reports/low-stock/reorder",
        headers=admin_headers,
        json={
            "product_ids": [p.id],
            "quantity_overrides": {str(p.id): 7},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["created_purchase_orders"]) == 1
    assert body["created_purchase_orders"][0]["total_amount"] == pytest.approx(70.0)


@pytest.mark.db
def test_reorder_skips_products_with_no_supplier(
    client: TestClient, admin_headers: dict, db: Session
):
    """Products with no SupplierProduct mapping can't be put on a draft
    PO (we need a supplier). They're reported back in `skipped` with
    reason 'no_supplier' so the UI can prompt the user to link a
    supplier first."""
    s = _seed_supplier(db, "Mapped Supplier")
    pMapped = _seed_product(db, "Mapped Product", "MAP-1", cost=5.0)
    pMapped.reorder_quantity = 2
    _link(db, pMapped, s, cost=5.0)
    pOrphan = _seed_product(db, "Orphan Product", "ORPH-1", cost=5.0)
    pOrphan.reorder_quantity = 2
    db.commit()

    response = client.post(
        "/api/v1/reports/low-stock/reorder",
        headers=admin_headers,
        json={"product_ids": [pMapped.id, pOrphan.id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["created_purchase_orders"]) == 1
    assert body["created_purchase_orders"][0]["product_count"] == 1
    assert len(body["skipped"]) == 1
    assert body["skipped"][0]["product_id"] == pOrphan.id
    assert body["skipped"][0]["product_name"] == "Orphan Product"
    assert body["skipped"][0]["reason"] == "no_supplier"


@pytest.mark.db
def test_reorder_empty_selection_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/reports/low-stock/reorder",
        headers=admin_headers,
        json={"product_ids": []},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.purchaseOrder.reorderEmptySelection"


@pytest.mark.db
def test_reorder_picks_primary_supplier_when_multiple_mapped(
    client: TestClient, admin_headers: dict, db: Session
):
    """A product linked to two suppliers — one primary, one not — must
    go onto the primary supplier's PO."""
    s_primary = _seed_supplier(db, "Primary Source")
    s_alternate = _seed_supplier(db, "Backup Source")
    p = _seed_product(db, "Multi-source", "MULTI-1", cost=20.0)
    p.reorder_quantity = 3
    _link(db, p, s_primary, cost=18.0, primary=True)
    _link(db, p, s_alternate, cost=22.0, primary=False)
    db.commit()

    response = client.post(
        "/api/v1/reports/low-stock/reorder",
        headers=admin_headers,
        json={"product_ids": [p.id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["created_purchase_orders"]) == 1
    po = body["created_purchase_orders"][0]
    assert po["supplier_id"] == s_primary.id
    assert po["total_amount"] == pytest.approx(54.0)
