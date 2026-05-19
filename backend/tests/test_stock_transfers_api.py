import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
)
from src.models.stock_transfer import (
    LOCATION_AMAZON_FBA,
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.schemas.product import ProductCreate
from src.services.inventory_service import inventory_service
from src.services.marketplaces.base import (
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)

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


# ---------------------------------------------------------------------------
# POST /stock-transfers/{id}/reconcile (manual inbound reconciliation)
# ---------------------------------------------------------------------------


def _ensure_marketplace_with_credential(db, name, user_id):
    """Insert (or fetch) a Marketplace + an attached healthy credential
    for the given user. Returns (Marketplace, MarketplaceCredential)."""
    mp = db.query(Marketplace).filter(Marketplace.name.ilike(name)).first()
    if mp is None:
        mp = Marketplace(name=name, api_base_url="https://example.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    cred = MarketplaceCredential(
        user_id=user_id, marketplace_id=mp.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return mp, cred


def _make_shipped_transfer_in_db(db, *, product_id, dest_location, created_by_id):
    transfer = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location=dest_location,
        status=StockTransferStatus.SHIPPED.value,
        external_inbound_id="EXT-RECON-1",
        created_by_id=created_by_id,
    )
    db.add(transfer)
    db.flush()
    db.add(StockTransferItem(
        transfer_id=transfer.id,
        product_id=product_id,
        qty_planned=10,
        qty_shipped=10,
        qty_received=0,
    ))
    db.commit()
    db.refresh(transfer)
    return transfer


def test_reconcile_endpoint_runs_against_amazon_and_returns_summary_plus_transfer(
    client: TestClient, db, admin_headers, test_admin_user,
):
    """The happy path: an Amazon FBA transfer, a healthy credential,
    and a connector that reports 4/10 received. The endpoint commits
    the delta, returns the summary, and includes the refreshed
    transfer so the UI can render without a follow-up GET."""
    product = _make_product(db, "RECON-AMZN-1")
    mp, _cred = _ensure_marketplace_with_credential(db, "Amazon", test_admin_user.id)
    # Listing keyed by ASIN — exercises the SKU fallback path the
    # Amazon flow depends on.
    db.add(MarketplaceListing(
        product_id=product.id, marketplace_id=mp.id,
        external_listing_id="B0000RECON01", sync_status="IN_SYNC",
    ))
    db.commit()
    transfer = _make_shipped_transfer_in_db(
        db, product_id=product.id, dest_location=LOCATION_AMAZON_FBA,
        created_by_id=test_admin_user.id,
    )

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="EXT-RECON-1",
            status="receiving",
            received_items=[InboundShipmentReceivedItem(
                external_listing_id="RECON-AMZN-1",
                sku="RECON-AMZN-1",
                received_quantity=4,
            )],
        )
    )

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.marketplace_service.marketplace_service.get_connector",
            return_value=fake_connector,
        ),
    ):
        response = client.post(
            f"/api/v1/stock-transfers/{transfer.id}/reconcile",
            headers=admin_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items_updated"] == 1
    assert body["total_received_added"] == 4
    assert body["status_before"] == "shipped"
    assert body["status_after"] == "partially_received"
    # Transfer payload embedded so the UI can refresh in one round-trip.
    assert body["transfer"]["id"] == transfer.id
    assert body["transfer"]["status"] == "partially_received"
    assert body["transfer"]["last_reconciled_at"] is not None


def test_reconcile_endpoint_404s_for_unknown_transfer(
    client: TestClient, admin_headers,
):
    response = client.post(
        "/api/v1/stock-transfers/9999999/reconcile", headers=admin_headers,
    )
    assert response.status_code == 404


def test_reconcile_endpoint_400s_when_destination_is_not_a_marketplace(
    client: TestClient, db, admin_headers, test_admin_user,
):
    """A transfer to an internal warehouse has no marketplace to poll
    — the endpoint refuses rather than silently doing nothing."""
    product = _make_product(db, "RECON-INTERNAL-1")
    transfer = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location="warehouse-b",  # Not in MARKETPLACE_INBOUND_TARGETS
        status=StockTransferStatus.SHIPPED.value,
        external_inbound_id=None,
        created_by_id=test_admin_user.id,
    )
    db.add(transfer)
    db.flush()
    db.add(StockTransferItem(
        transfer_id=transfer.id, product_id=product.id,
        qty_planned=1, qty_shipped=1, qty_received=0,
    ))
    db.commit()

    response = client.post(
        f"/api/v1/stock-transfers/{transfer.id}/reconcile",
        headers=admin_headers,
    )
    assert response.status_code == 400
    body = response.json()
    # Body shape comes from LocalizedHTTPException: it carries the
    # localizable error code so the frontend interceptor renders the
    # right translated string. Detail string is the operator-friendly
    # fallback.
    assert "code" in body.get("detail", {}) or "warehouse" in response.text


def test_reconcile_endpoint_400s_when_no_credential_available(
    client: TestClient, db, admin_headers, test_admin_user,
):
    """An Amazon FBA transfer whose creator has no Amazon credential
    AND there's no fallback credential available → 400 with a clear
    message so the operator knows to connect the marketplace."""
    product = _make_product(db, "RECON-NOCRED-1")
    # Create the Marketplace but NO credential.
    mp = db.query(Marketplace).filter(Marketplace.name == "Amazon").first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://example.com")
        db.add(mp)
        db.commit()
    # Wipe any credential rows for the admin user on the Amazon mp so
    # the fallback can't pick one up.
    db.query(MarketplaceCredential).filter(
        MarketplaceCredential.marketplace_id == mp.id,
    ).delete()
    db.commit()

    transfer = _make_shipped_transfer_in_db(
        db, product_id=product.id, dest_location=LOCATION_AMAZON_FBA,
        created_by_id=test_admin_user.id,
    )

    response = client.post(
        f"/api/v1/stock-transfers/{transfer.id}/reconcile",
        headers=admin_headers,
    )
    assert response.status_code == 400
