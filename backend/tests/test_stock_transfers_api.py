import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.stock_transfer import LOCATION_INTERNAL, LOCATION_ML_FULL
from src.schemas.product import ProductCreate
from src.services.inventory_service import inventory_service

pytestmark = pytest.mark.db


def _make_product(db, sku: str):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"API Transfer {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _seed_internal_stock(db, product_id: int, qty: int):
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=qty,
        reason="seed",
        location=LOCATION_INTERNAL,
    )
    db.commit()


def _stock_at(db, product_id: int, location: str) -> int:
    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == product_id,
            InventoryItem.location == location,
        )
        .first()
    )
    return item.quantity if item else 0


def test_api_create_list_and_get_transfer(client: TestClient, db, admin_headers):
    product = _make_product(db, "API-CR-1")
    response = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 12}],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "draft"
    assert data["dest_location"] == LOCATION_ML_FULL
    assert len(data["items"]) == 1
    assert data["items"][0]["qty_planned"] == 12
    transfer_id = data["id"]

    list_resp = client.get("/api/v1/stock-transfers/", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(t["id"] == transfer_id for t in list_resp.json())

    get_resp = client.get(f"/api/v1/stock-transfers/{transfer_id}", headers=admin_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == transfer_id


def test_api_list_filter_by_status(client: TestClient, db, admin_headers):
    product = _make_product(db, "API-FILTER-1")
    _seed_internal_stock(db, product.id, 50)
    draft_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 10}],
        },
    )
    draft_id = draft_resp.json()["id"]

    shipped_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 5}],
        },
    )
    shipped_id = shipped_resp.json()["id"]
    client.post(f"/api/v1/stock-transfers/{shipped_id}/ship", headers=admin_headers)

    draft_only = client.get(
        "/api/v1/stock-transfers/?status=draft", headers=admin_headers
    ).json()
    shipped_only = client.get(
        "/api/v1/stock-transfers/?status=shipped", headers=admin_headers
    ).json()
    assert any(t["id"] == draft_id for t in draft_only)
    assert all(t["id"] != shipped_id for t in draft_only)
    assert any(t["id"] == shipped_id for t in shipped_only)


def test_api_ship_and_receive_flow(client: TestClient, db, admin_headers):
    product = _make_product(db, "API-FLOW-1")
    _seed_internal_stock(db, product.id, 40)

    create_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 25}],
        },
    )
    transfer_id = create_resp.json()["id"]

    ship_resp = client.post(
        f"/api/v1/stock-transfers/{transfer_id}/ship", headers=admin_headers
    )
    assert ship_resp.status_code == 200, ship_resp.text
    assert ship_resp.json()["status"] == "shipped"
    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 15

    partial_resp = client.post(
        f"/api/v1/stock-transfers/{transfer_id}/receive",
        headers=admin_headers,
        json=[{"product_id": product.id, "quantity": 10}],
    )
    assert partial_resp.status_code == 200, partial_resp.text
    assert partial_resp.json()["status"] == "partially_received"
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 10

    final_resp = client.post(
        f"/api/v1/stock-transfers/{transfer_id}/receive",
        headers=admin_headers,
        json=[{"product_id": product.id, "quantity": 15}],
    )
    assert final_resp.status_code == 200, final_resp.text
    assert final_resp.json()["status"] == "received"
    assert _stock_at(db, product.id, LOCATION_ML_FULL) == 25
    assert _stock_at(db, product.id, LOCATION_INTERNAL) == 15


def test_api_cannot_ship_with_insufficient_stock(client: TestClient, db, admin_headers):
    product = _make_product(db, "API-INSUF")
    _seed_internal_stock(db, product.id, 3)

    create_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 10}],
        },
    )
    transfer_id = create_resp.json()["id"]

    ship_resp = client.post(
        f"/api/v1/stock-transfers/{transfer_id}/ship", headers=admin_headers
    )
    assert ship_resp.status_code == 400
    assert "Insufficient" in ship_resp.json()["detail"]


def test_api_update_draft(client: TestClient, db, admin_headers):
    a = _make_product(db, "API-UP-A")
    b = _make_product(db, "API-UP-B")
    create_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": a.id, "qty_planned": 5}],
        },
    )
    transfer_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/stock-transfers/{transfer_id}",
        headers=admin_headers,
        json={
            "notes": "edited",
            "items": [
                {"product_id": a.id, "qty_planned": 9},
                {"product_id": b.id, "qty_planned": 4},
            ],
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    data = update_resp.json()
    assert data["notes"] == "edited"
    qty_by_product = {item["product_id"]: item["qty_planned"] for item in data["items"]}
    assert qty_by_product == {a.id: 9, b.id: 4}


def test_api_cancel_and_delete_draft(client: TestClient, db, admin_headers):
    product = _make_product(db, "API-DEL")
    create_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": product.id, "qty_planned": 5}],
        },
    )
    transfer_id = create_resp.json()["id"]

    cancel_resp = client.post(
        f"/api/v1/stock-transfers/{transfer_id}/cancel", headers=admin_headers
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    delete_resp = client.delete(
        f"/api/v1/stock-transfers/{transfer_id}", headers=admin_headers
    )
    assert delete_resp.status_code == 200

    after = client.get(f"/api/v1/stock-transfers/{transfer_id}", headers=admin_headers)
    assert after.status_code == 404
