import pytest
from fastapi.testclient import TestClient
from src.schemas.supplier import SupplierCreate
from src.crud.crud_supplier import supplier as crud_supplier

# Mark all tests as requiring database
pytestmark = pytest.mark.db

@pytest.mark.db
def test_create_purchase_order_api(client: TestClient, db):
    # 1. Create Supplier
    supplier_in = SupplierCreate(name="API Test Supplier")
    supplier = crud_supplier.create(db=db, obj_in=supplier_in)
    
    # 2. Create PO via API
    response = client.post(
        "/api/v1/purchase-orders/",
        json={
            "supplier_id": supplier.id,
            "status": "draft",
            "currency": "USD",
            "items": []
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["supplier_id"] == supplier.id
    assert data["status"] == "draft"
    assert "id" in data

@pytest.mark.db
def test_transition_status_api(client: TestClient, db):
    # 1. Create Supplier & PO
    supplier_in = SupplierCreate(name="Status API Supplier")
    supplier = crud_supplier.create(db=db, obj_in=supplier_in)
    
    po_resp = client.post(
        "/api/v1/purchase-orders/",
        json={"supplier_id": supplier.id, "status": "draft"}
    )
    po_id = po_resp.json()["id"]
    
    # 2. Transition Status
    response = client.post(f"/api/v1/purchase-orders/{po_id}/status", params={"status": "ordered"})
    assert response.status_code == 200
    assert response.json()["status"] == "ordered"
