import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.stock_transfer import (
    LOCATION_AMAZON_FBA,
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
)
from src.schemas.product import ProductCreate
from src.services.inventory_service import inventory_service


pytestmark = pytest.mark.db


def _make_product(db, sku: str):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Plan API {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _seed_internal(db, product_id: int, qty: int):
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=qty,
        reason="seed",
        location=LOCATION_INTERNAL,
    )
    db.commit()


def test_api_inventory_snapshot_returns_rows(client: TestClient, db, admin_headers):
    a = _make_product(db, "API-SNAP")
    _seed_internal(db, a.id, 25)

    response = client.get(
        "/api/v1/stock-transfers/inventory-snapshot", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    rows = {r["product_id"]: r for r in response.json()}
    assert a.id in rows
    assert rows[a.id]["by_location"][LOCATION_INTERNAL] == 25


def test_api_plan_allocations_creates_drafts(client: TestClient, db, admin_headers):
    a = _make_product(db, "API-PLAN-A")
    b = _make_product(db, "API-PLAN-B")
    _seed_internal(db, a.id, 100)
    _seed_internal(db, b.id, 100)

    response = client.post(
        "/api/v1/stock-transfers/plan-allocations",
        headers=admin_headers,
        json={
            "notes": "API plan",
            "allocations": [
                {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 30},
                {"product_id": b.id, "dest_location": LOCATION_AMAZON_FBA, "qty_planned": 25},
                {"product_id": b.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 10},
            ],
        },
    )
    assert response.status_code == 200, response.text
    drafts = response.json()
    assert len(drafts) == 2
    by_dest = {d["dest_location"]: d for d in drafts}
    assert sorted(item["product_id"] for item in by_dest[LOCATION_ML_FULL]["items"]) == sorted(
        [a.id, b.id]
    )


def test_api_plan_allocations_rejects_overcommit(client: TestClient, db, admin_headers):
    a = _make_product(db, "API-OVER")
    _seed_internal(db, a.id, 5)

    response = client.post(
        "/api/v1/stock-transfers/plan-allocations",
        headers=admin_headers,
        json={
            "allocations": [
                {"product_id": a.id, "dest_location": LOCATION_ML_FULL, "qty_planned": 10},
            ],
        },
    )
    assert response.status_code == 400
    assert "exceed internal stock" in response.json()["detail"]


def test_api_reconciliation_endpoint(client: TestClient, db, admin_headers):
    a = _make_product(db, "API-REC")
    _seed_internal(db, a.id, 50)
    create_resp = client.post(
        "/api/v1/stock-transfers/",
        headers=admin_headers,
        json={
            "dest_location": LOCATION_ML_FULL,
            "items": [{"product_id": a.id, "qty_planned": 20}],
        },
    )
    tid = create_resp.json()["id"]
    client.post(f"/api/v1/stock-transfers/{tid}/ship", headers=admin_headers)
    client.post(
        f"/api/v1/stock-transfers/{tid}/receive",
        headers=admin_headers,
        json=[{"product_id": a.id, "quantity": 18}],
    )

    response = client.get("/api/v1/stock-transfers/reconciliation", headers=admin_headers)
    assert response.status_code == 200, response.text
    row = next(r for r in response.json() if r["transfer_id"] == tid)
    assert row["qty_shipped"] == 20
    assert row["qty_received"] == 18
    assert row["delta"] == -2
