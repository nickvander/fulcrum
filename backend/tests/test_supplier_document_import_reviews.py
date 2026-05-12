import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.models.inventory import InventoryAdjustment
from src.models.supplier_product import SupplierProduct
from src.models.supplier_product_alias import SupplierProductAlias
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

UNMATCHED_SAMPLE_BYTES = b"""Supplier: Alibaba Launch Supplier
Order #ALI-UNMATCHED-1002
Currency USD

SKU Description Qty Unit Price Total
ALI-NEW-001 Alibaba New Customer Widget 3 $14.25 $42.75

Grand Total $42.75
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


def test_import_review_line_can_create_product_and_continue_to_approval(
    client: TestClient,
    db,
    admin_headers,
):
    supplier = crud_supplier.create(
        db=db,
        obj_in=SupplierCreate(name="Alibaba Launch Supplier", currency="USD"),
    )
    review_response = client.post(
        "/api/v1/purchase-orders/imports/reviews",
        files={"file": ("alibaba_unmatched_sample.txt", UNMATCHED_SAMPLE_BYTES, "text/plain")},
        headers=admin_headers,
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["warnings"] == ["1 line item(s) need a Fulcrum product match before approval."]
    assert review["extracted_data"]["items"][0]["matched_product_id"] is None

    assist_response = client.post(
        f"/api/v1/purchase-orders/imports/reviews/{review['id']}/items/0/create-product",
        json={
            "supplier_id": supplier.id,
            "create_alias": True,
        },
        headers=admin_headers,
    )

    assert assist_response.status_code == 200
    assisted = assist_response.json()
    product = assisted["product"]
    assert product["sku"] == "ALI-NEW-001"
    assert product["name"] == "Alibaba New Customer Widget"
    assert assisted["import_review"]["warnings"] == []
    assert assisted["import_review"]["supplier_id"] == supplier.id
    assert assisted["import_review"]["extracted_data"]["items"][0]["matched_product_id"] == product["id"]
    assert assisted["alias"]["alias_sku"] == "ALI-NEW-001"
    assert (
        db.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == supplier.id, SupplierProduct.product_id == product["id"])
        .count()
        == 1
    )

    approval_response = client.post(
        f"/api/v1/purchase-orders/imports/reviews/{review['id']}/approve",
        json={
            "supplier_id": supplier.id,
            "currency": "USD",
            "shipping_cost": 0.0,
            "tax_amount": 0.0,
            "items": assisted["import_review"]["extracted_data"]["items"],
        },
        headers=admin_headers,
    )

    assert approval_response.status_code == 200
    po = approval_response.json()["purchase_order"]
    assert po["status"] == "draft"
    assert po["items"][0]["product_id"] == product["id"]
    assert db.query(InventoryAdjustment).filter(InventoryAdjustment.product_id == product["id"]).count() == 0


def test_import_review_line_can_learn_alias_for_existing_product(
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
            name="Warehouse Shelf Bin",
            sku="FULCRUM-BIN-1",
            default_resale_price=30.0,
            cost_price=14.25,
        ),
    )
    review_response = client.post(
        "/api/v1/purchase-orders/imports/reviews",
        files={"file": ("alibaba_unmatched_sample.txt", UNMATCHED_SAMPLE_BYTES, "text/plain")},
        headers=admin_headers,
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["extracted_data"]["items"][0]["matched_product_id"] is None

    assist_response = client.post(
        f"/api/v1/purchase-orders/imports/reviews/{review['id']}/items/0/learn-alias",
        json={
            "supplier_id": supplier.id,
            "product_id": product.id,
        },
        headers=admin_headers,
    )

    assert assist_response.status_code == 200
    assisted = assist_response.json()
    assert assisted["import_review"]["warnings"] == []
    assert assisted["import_review"]["extracted_data"]["items"][0]["matched_product_id"] == product.id
    assert assisted["alias"]["alias_sku"] == "ALI-NEW-001"
    assert assisted["alias"]["alias_name"] == "Alibaba New Customer Widget"
    assert (
        db.query(SupplierProductAlias)
        .filter(
            SupplierProductAlias.supplier_id == supplier.id,
            SupplierProductAlias.product_id == product.id,
            SupplierProductAlias.alias_sku == "ALI-NEW-001",
        )
        .count()
        == 1
    )

    next_review_response = client.post(
        "/api/v1/purchase-orders/imports/reviews",
        files={"file": ("alibaba_unmatched_again.txt", UNMATCHED_SAMPLE_BYTES, "text/plain")},
        headers=admin_headers,
    )
    assert next_review_response.status_code == 200
    next_review = next_review_response.json()
    assert next_review["warnings"] == []
    assert next_review["extracted_data"]["items"][0]["matched_product_id"] == product.id
