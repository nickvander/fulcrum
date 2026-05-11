import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
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


@pytest.mark.db
def test_purchase_order_list_query_count_stays_bounded(client: TestClient, db):
    from src.crud import crud_product
    from src.schemas.product import ProductCreate

    supplier_in = SupplierCreate(name="PO Query Count Supplier")
    supplier = crud_supplier.create(db=db, obj_in=supplier_in)
    products = [
        crud_product.product.create(
            db=db,
            obj_in=ProductCreate(
                name=f"PO Query Product {index}",
                sku=f"PO-QUERY-{index}",
                default_resale_price=20.0,
                cost_price=10.0,
            ),
        )
        for index in range(4)
    ]

    for index in range(6):
        response = client.post(
            "/api/v1/purchase-orders/",
            json={
                "supplier_id": supplier.id,
                "status": "ordered",
                "currency": "USD",
                "items": [
                    {
                        "product_id": products[index % len(products)].id,
                        "quantity_ordered": 2,
                        "unit_cost": 10.0,
                    }
                ],
            },
        )
        assert response.status_code == 200

    statements = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.get("/api/v1/purchase-orders/?limit=100")
    finally:
        event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    assert len(response.json()) >= 6
    assert len(statements) <= 10
