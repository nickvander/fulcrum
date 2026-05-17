"""Localized error wire-shape tests for purchase_orders.py.

46 raise sites collapse to ~20 distinct codes; this covers the
highest-frequency / highest-visibility ones rather than 1:1 by site.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.db
def test_get_missing_po_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/purchase-orders/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Purchase Order not found",
        "code": "apiErrors.purchaseOrder.notFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_delete_missing_po_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.delete("/api/v1/purchase-orders/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "apiErrors.purchaseOrder.notFound"
    assert body["params"] == {"id": 999999}


@pytest.mark.db
def test_apply_cost_allocation_without_confirm_returns_localized_mustConfirmCosts(
    client: TestClient, admin_headers: dict, db: Session
):
    """The /costs/apply endpoint refuses to act without confirm=True
    so the user can't accidentally rewrite landed costs."""
    # Seed a minimal PO so the cost-allocation handler reaches the
    # confirm check before bailing on something else.
    from src.models.purchase_order import PurchaseOrder
    from src.models.supplier import Supplier
    sup = Supplier(name="Cost-Test Supplier")
    db.add(sup)
    db.flush()
    po = PurchaseOrder(
        supplier_id=sup.id,
        status="received",
        shipping_cost=10.0,
        other_costs=0.0,
        tax_amount=0.0,
    )
    db.add(po)
    db.commit()

    response = client.post(
        f"/api/v1/purchase-orders/{po.id}/costs/apply",
        headers=admin_headers,
        json={"confirm": False, "excluded_items": []},
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Must confirm=True to apply costs",
        "code": "apiErrors.purchaseOrder.mustConfirmCosts",
        "params": {},
    }


@pytest.mark.db
def test_cost_allocation_for_missing_po_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/purchase-orders/999999/costs/apply",
        headers=admin_headers,
        json={"confirm": True, "excluded_items": []},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "apiErrors.purchaseOrder.notFound"
    assert body["params"] == {"id": 999999}


@pytest.mark.db
def test_import_review_not_found_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    response = client.get(
        "/api/v1/purchase-orders/imports/reviews/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Import review not found",
        "code": "apiErrors.purchaseOrder.importReviewNotFound",
        "params": {},
    }


@pytest.mark.db
def test_bulk_reject_without_scope_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    """Bulk-reject endpoint refuses an empty body to avoid rejecting every
    pending review by accident."""
    response = client.post(
        "/api/v1/purchase-orders/imports/reviews/bulk-reject",
        headers=admin_headers,
        json={},  # neither review_ids nor stale_before
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Provide review_ids or stale_before to bulk reject reviews.",
        "code": "apiErrors.purchaseOrder.bulkRejectMissingScope",
        "params": {},
    }
