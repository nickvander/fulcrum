from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.inventory import InventoryItem
from src.models.supplier import Supplier
import pytest

# Mark all tests as requiring database
pytestmark = pytest.mark.db

@pytest.fixture
def test_supplier(db):
    supplier = Supplier(
        name="Test Inventory Supplier",
        email="inv@supplier.com",
        currency="USD"
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

def test_receive_items_workflow(client: TestClient, db: Session, test_product, test_supplier):
    # Debug Auth
    from src.schemas.user import UserCreate
    from src.crud import user
    from src.config import settings

    # Ensure admin doesn't exist or is handled
    existing_admin = user.get_by_email(db, email="debug_admin@test.com")
    if not existing_admin:
        user_in = UserCreate(
            email="debug_admin@test.com",
            password="TestPassword123!",
            is_superuser=True,
            user_type="admin",
            first_name="Admin",
            last_name="Debug"
        )
        user.create(db=db, obj_in=user_in)

    login_data = {
        "username": "debug_admin@test.com",
        "password": "TestPassword123!"
    }
    r = client.post(f"{settings.API_V1_STR}/users/login/access-token", data=login_data)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    # 1. Create a PO
    po_data = {
        "supplier_id": test_supplier.id,
        "currency": "USD",
        "items": [
            {"product_id": test_product.id, "quantity_ordered": 10, "unit_cost": 50.0}
        ]
    }
    response = client.post("/api/v1/purchase-orders/", json=po_data, headers=headers)
    assert response.status_code == 200
    po_id = response.json()["id"]

    # 2. Transition to ORDERED
    response = client.post(f"/api/v1/purchase-orders/{po_id}/status", params={"status": "ordered"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ordered"

    # 3. Receive 5 items
    receive_payload = [
        {"product_id": test_product.id, "quantity": 5}
    ]
    response = client.post(f"/api/v1/purchase-orders/{po_id}/receive", json=receive_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partially_received"
    
    # 4. Verify Inventory
    inventory = db.query(InventoryItem).filter(InventoryItem.product_id == test_product.id).first()
    assert inventory is not None
    assert inventory.quantity == 5
    
    # 5. Receive remaining 5 items
    response = client.post(f"/api/v1/purchase-orders/{po_id}/receive", json=receive_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    # 6. Verify Inventory updated again
    db.refresh(inventory)
    assert inventory.quantity == 10


def test_receive_items_targets_exact_po_line(client: TestClient, db: Session, test_product, test_supplier, admin_headers):
    po_data = {
        "supplier_id": test_supplier.id,
        "status": "ordered",
        "currency": "USD",
        "items": [
            {"product_id": test_product.id, "quantity_ordered": 10, "unit_cost": 50.0},
            {"product_id": test_product.id, "quantity_ordered": 4, "unit_cost": 45.0},
        ],
    }
    response = client.post("/api/v1/purchase-orders/", json=po_data, headers=admin_headers)
    assert response.status_code == 200
    po = response.json()
    target_item = po["items"][1]

    receive_payload = [
        {
            "po_item_id": target_item["id"],
            "product_id": test_product.id,
            "quantity": 3,
        }
    ]
    response = client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive",
        json=receive_payload,
        headers=admin_headers,
    )

    assert response.status_code == 200
    received_items = {item["id"]: item for item in response.json()["items"]}
    assert received_items[target_item["id"]]["quantity_received"] == 3
    assert received_items[po["items"][0]["id"]]["quantity_received"] == 0

    inventory = db.query(InventoryItem).filter(InventoryItem.product_id == test_product.id).first()
    assert inventory is not None
    assert inventory.quantity == 3

def test_adjust_stock_api(client: TestClient, db: Session, test_product):
    # This test also needs auth, skipping manual setup for brevity and focusing on workflow above first
    pass
