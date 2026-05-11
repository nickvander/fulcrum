import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.models.inventory import InventoryAdjustment
from src.schemas.product import ProductCreate
from src.schemas.supplier import SupplierCreate


pytestmark = pytest.mark.db


SAMPLE_BYTES = b"""Supplier: Alibaba Launch Supplier
Order #ALI-READY-1001
Order date 05/11/2026
Currency USD

SKU Description Qty Unit Price Total
ALI-DEMO-WIDGET-001 Alibaba Demo Starter Widget 5 $12.50 $62.50

Subtotal $62.50
Shipping $8.00
Tax $0.00
Grand Total $70.50
"""


def test_supplier_document_import_review_approves_to_draft_po_without_stock_change(
    client: TestClient,
    db,
    admin_headers,
):
    supplier = crud_supplier.create(
        db=db,
        obj_in=SupplierCreate(name="Alibaba Launch Supplier", currency="USD"),
    )
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="Alibaba Demo Starter Widget",
            sku="ALI-DEMO-WIDGET-001",
            default_resale_price=29.0,
            cost_price=12.5,
        ),
    )

    review_response = client.post(
        "/api/v1/purchase-orders/imports/reviews",
        files={"file": ("alibaba_import_review_sample.txt", SAMPLE_BYTES, "text/plain")},
        headers=admin_headers,
    )

    assert review_response.status_code == 200
    review = review_response.json()
    assert review["status"] == "pending"
    assert review["mode"] == "create"
    assert review["supplier_id"] == supplier.id
    assert review["extracted_data"]["vendor_name"] == "Alibaba Launch Supplier"
    assert review["extracted_data"]["items"][0]["matched_product_id"] == product.id

    queue_response = client.get(
        "/api/v1/purchase-orders/imports/reviews",
        headers=admin_headers,
    )
    assert queue_response.status_code == 200
    assert any(item["id"] == review["id"] for item in queue_response.json())

    approval_response = client.post(
        f"/api/v1/purchase-orders/imports/reviews/{review['id']}/approve",
        json={
            "supplier_id": supplier.id,
            "currency": "USD",
            "shipping_cost": 8.0,
            "tax_amount": 0.0,
            "notes": "Approved from import review test",
            "items": review["extracted_data"]["items"],
        },
        headers=admin_headers,
    )

    assert approval_response.status_code == 200
    approved = approval_response.json()
    po = approved["purchase_order"]
    assert approved["import_review"]["status"] == "approved"
    assert po["status"] == "draft"
    assert po["supplier_id"] == supplier.id
    assert po["items"][0]["product_id"] == product.id
    assert po["items"][0]["quantity_ordered"] == 5
    assert db.query(InventoryAdjustment).filter(InventoryAdjustment.product_id == product.id).count() == 0


def test_supplier_document_import_review_can_be_rejected(
    client: TestClient,
    db,
    admin_headers,
):
    crud_supplier.create(
        db=db,
        obj_in=SupplierCreate(name="Alibaba Launch Supplier", currency="USD"),
    )

    review_response = client.post(
        "/api/v1/purchase-orders/imports/reviews",
        files={"file": ("alibaba_import_review_sample.txt", SAMPLE_BYTES, "text/plain")},
        headers=admin_headers,
    )
    assert review_response.status_code == 200

    review_id = review_response.json()["id"]
    reject_response = client.post(
        f"/api/v1/purchase-orders/imports/reviews/{review_id}/reject",
        headers=admin_headers,
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
