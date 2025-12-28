
import pytest
from fastapi.testclient import TestClient
from src.schemas.supplier import SupplierCreate
from src.schemas.product import ProductCreate
from src.crud.crud_supplier import supplier as crud_supplier
from src.crud.crud_product import product as crud_product

# Mark all tests as requiring database
pytestmark = pytest.mark.db

@pytest.mark.db
def test_delete_po_safety(client: TestClient, db, admin_headers):
    # 1. Setup Data: Supplier & Product
    supplier = crud_supplier.create(db=db, obj_in=SupplierCreate(name="Delete Safety Supplier"))
    product = crud_product.create(db=db, obj_in=ProductCreate(name="Test Product", sku="TEST-DEL", cost_price=10.0))
    
    # 2. Create PO with Items
    po_resp = client.post(
        "/api/v1/purchase-orders/",
        json={
            "supplier_id": supplier.id,
            "status": "ordered",
            "items": [
                {"product_id": product.id, "quantity_ordered": 10, "unit_cost": 10.0}
            ]
        }
    )
    assert po_resp.status_code == 200
    po_id = po_resp.json()["id"]

    # 3. Receive Items (Partially)
    receive_resp = client.post(
        f"/api/v1/purchase-orders/{po_id}/receive",
        json=[{"product_id": product.id, "quantity": 5}],
        headers=admin_headers
    )
    assert receive_resp.status_code == 200

    # 4. Attempt Deletion - Should FAIL (400)
    delete_resp = client.delete(f"/api/v1/purchase-orders/{po_id}")
    assert delete_resp.status_code == 400
    assert "items have already been received" in delete_resp.json()["detail"]

    # 5. Create another PO (No receipts)
    po_resp_clean = client.post(
        "/api/v1/purchase-orders/",
        json={
            "supplier_id": supplier.id,
            "status": "draft",
            "items": []
        }
    )
    po_id_clean = po_resp_clean.json()["id"]

    # 6. Attempt Deletion - Should PASS (200)
    delete_resp_clean = client.delete(f"/api/v1/purchase-orders/{po_id_clean}")
    assert delete_resp_clean.status_code == 200
    assert delete_resp_clean.json()["id"] == po_id_clean
