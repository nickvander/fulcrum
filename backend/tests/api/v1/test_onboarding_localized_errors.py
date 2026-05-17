"""Localized error wire-shape tests for onboarding.py.

The cleanup-blocked 409 uses a non-standard nested `detail` (object with
message + blocked_reasons + records) that the dashboard component reads
to render an inline list. The migration preserves the nested structure
and adds a `code` field so the frontend interceptor can translate the
snackbar via transloco while the component still has access to the
structured payload.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.db
def test_cleanup_demo_without_confirmation_returns_localized_payload(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/onboarding/demo-data/cleanup",
        headers=admin_headers,
        json={"confirm": False},
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Demo data cleanup must be confirmed.",
        "code": "apiErrors.onboarding.cleanupNotConfirmed",
        "params": {},
    }


@pytest.mark.db
def test_cleanup_demo_blocked_preserves_nested_detail_with_code(
    client: TestClient, admin_headers: dict, db
):
    """When a demo product has real customer orders attached, cleanup is
    refused with a 409 carrying both the standard `code` for snackbar
    translation AND the nested detail payload (blocked_reasons + records)
    that the dashboard renders inline."""
    # Seed a demo workspace, then add a sales order against the demo
    # product so cleanup is blocked.
    create_resp = client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)
    assert create_resp.status_code == 200
    demo = create_resp.json()
    demo_product_id = demo["product_id"]

    from src.models.order import SalesOrder, SalesOrderItem, OrderSource
    from src.models.product import Product
    product = db.query(Product).filter(Product.id == demo_product_id).one()
    sales_order = SalesOrder(
        status="completed",
        total_price=1.0,
        source=OrderSource.FULCRUM,
        external_order_id="LIVE-ORDER-1",
    )
    db.add(sales_order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=sales_order.id,
        product_id=product.id,
        quantity=1,
        price_per_unit=1.0,
    ))
    db.commit()

    response = client.post(
        "/api/v1/onboarding/demo-data/cleanup",
        headers=admin_headers,
        json={"confirm": True},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "apiErrors.onboarding.cleanupBlocked"
    # Nested detail must still be present for the dashboard component
    assert isinstance(body["detail"], dict)
    assert body["detail"]["message"] == "Demo data cleanup was blocked to protect customer records."
    assert "blocked_reasons" in body["detail"]
    assert "records" in body["detail"]
