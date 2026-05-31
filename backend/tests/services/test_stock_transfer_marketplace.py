"""
Slice-2 tests: stock-transfer integration with marketplace connectors
and listing-quantity sync.
"""
import pytest
from unittest.mock import patch, AsyncMock

from src.crud import crud_product
from src.models.marketplace import Marketplace, MarketplaceListing
from src.models.stock_transfer import (
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransferStatus,
)
from src.schemas.product import ProductCreate
from src.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferItemCreate,
    StockTransferReceiveItem,
)
from src.services.inventory_service import inventory_service
from src.services.marketplaces.base import InboundShipmentResult
from src.services.stock_transfer_service import stock_transfer_service


pytestmark = pytest.mark.db


def _make_product(db, sku: str):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"MP Transfer {sku}",
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


def _ensure_marketplace(db, name: str = "MercadoLibre") -> Marketplace:
    existing = db.query(Marketplace).filter(Marketplace.name == name).first()
    if existing:
        return existing
    mp = Marketplace(name=name, api_base_url="https://api.mercadolibre.com")
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return mp


def test_ship_pushes_to_marketplace_when_flag_set(db):
    product = _make_product(db, "MP-SHIP-1")
    _seed_internal_stock(db, product.id, 50)
    _ensure_marketplace(db)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )

    stub_result = InboundShipmentResult(
        external_inbound_id="ML-FULL-STUB-EXT-42",
        status="pending",
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.create_inbound_shipment",
        new=AsyncMock(return_value=stub_result),
    ) as mocked:
        shipped = stock_transfer_service.ship(
            db=db, transfer_id=transfer.id, push_to_marketplace=True
        )

    mocked.assert_awaited_once()
    assert shipped.status == StockTransferStatus.SHIPPED.value
    assert shipped.external_inbound_id == "ML-FULL-STUB-EXT-42"


def test_ship_push_with_reauth_credential_ships_but_raises_reauth(db, test_admin_user):
    """
    When push_to_marketplace=True but the user's ML credential is flagged
    needs_reauthorization, the inventory move + SHIPPED status must STILL
    persist (the ship is legitimate), the connector must NOT be called, and
    the service must raise ReauthorizationRequiredError so the endpoint can
    surface an inline Reconnect prompt. external_inbound_id stays NULL.
    """
    from src.crud.crud_marketplace_credential import (
        marketplace_credential as crud_cred,
    )
    from src.schemas.marketplace_credential import MarketplaceCredentialCreate
    from src.services.marketplace_service import ReauthorizationRequiredError

    product = _make_product(db, "MP-SHIP-REAUTH")
    _seed_internal_stock(db, product.id, 50)
    mp = _ensure_marketplace(db)

    cred = crud_cred.create_with_owner(
        db,
        obj_in=MarketplaceCredentialCreate(
            marketplace_id=mp.id,
            access_token="stale",
            refresh_token="dead",
        ),
        user_id=test_admin_user.id,
    )
    cred.needs_reauthorization = True
    cred.last_refresh_error = "refresh denied: invalid_grant"
    db.commit()

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
        user=test_admin_user,
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.create_inbound_shipment",
        new=AsyncMock(return_value=InboundShipmentResult(external_inbound_id="SHOULD-NOT")),
    ) as mocked:
        with pytest.raises(ReauthorizationRequiredError):
            stock_transfer_service.ship(
                db=db,
                transfer_id=transfer.id,
                user=test_admin_user,
                push_to_marketplace=True,
            )

    # The connector was never invoked because the credential is dead.
    mocked.assert_not_called()

    # Critical: the ship still persisted even though the push raised.
    db.expire_all()
    refreshed = stock_transfer_service._get_or_404(db, transfer.id)
    assert refreshed.status == StockTransferStatus.SHIPPED.value
    assert refreshed.external_inbound_id is None
    assert refreshed.shipped_at is not None
    # And the inventory actually left the source location.
    from src.models.inventory import InventoryItem
    from src.models.stock_transfer import LOCATION_INTERNAL as _INTERNAL
    from sqlalchemy.sql import func
    remaining = (
        db.query(func.coalesce(func.sum(InventoryItem.quantity), 0))
        .filter(
            InventoryItem.product_id == product.id,
            InventoryItem.location == _INTERNAL,
        )
        .scalar()
    )
    assert remaining == 40


def test_ship_push_with_no_credential_is_graceful(db, test_admin_user):
    """
    push_to_marketplace=True with NO credential configured must remain the
    graceful manual-fallback path: the transfer ships, no reauth is raised,
    and external_inbound_id is left NULL (operator does the inbound by hand).
    """
    product = _make_product(db, "MP-SHIP-NOCRED")
    _seed_internal_stock(db, product.id, 50)
    _ensure_marketplace(db)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
        user=test_admin_user,
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.create_inbound_shipment",
        new=AsyncMock(return_value=InboundShipmentResult(external_inbound_id="STUB")),
    ) as mocked:
        shipped = stock_transfer_service.ship(
            db=db,
            transfer_id=transfer.id,
            user=test_admin_user,
            push_to_marketplace=True,
        )

    # With no credential, token is None and the connector is still called
    # (the manual/stub connector path), but no reauth error is raised.
    assert shipped.status == StockTransferStatus.SHIPPED.value
    mocked.assert_awaited_once()


def test_ship_without_flag_does_not_call_marketplace(db):
    product = _make_product(db, "MP-SHIP-2")
    _seed_internal_stock(db, product.id, 50)
    _ensure_marketplace(db)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=10)],
        ),
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.create_inbound_shipment",
        new=AsyncMock(return_value=InboundShipmentResult(external_inbound_id="X")),
    ) as mocked:
        shipped = stock_transfer_service.ship(db=db, transfer_id=transfer.id)

    mocked.assert_not_called()
    assert shipped.external_inbound_id is None


def test_sync_listings_updates_quantity_on_existing_listing(db):
    product = _make_product(db, "MP-SYNC-1")
    _seed_internal_stock(db, product.id, 50)
    mp = _ensure_marketplace(db)

    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=mp.id,
        external_listing_id="MLM-PRESENT-1",
        status="active",
        sync_status="SYNCED",
    )
    db.add(listing)
    db.commit()

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=15)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=15)],
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.sync_inventory",
        new=AsyncMock(return_value=True),
    ) as mocked:
        summary = stock_transfer_service.sync_marketplace_listings(
            db=db, transfer_id=transfer.id
        )

    mocked.assert_awaited_once_with("MLM-PRESENT-1", 15, access_token=None)
    assert summary["updated"][0]["ok"] is True
    assert summary["updated"][0]["qty"] == 15
    assert summary["missing_listings"] == []

    db.refresh(listing)
    assert listing.available_quantity == 15
    assert listing.sync_status == "SYNCED"


def test_sync_listings_reports_missing_listing(db):
    product = _make_product(db, "MP-SYNC-MISSING")
    _seed_internal_stock(db, product.id, 30)
    _ensure_marketplace(db)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=8)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=8)],
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.sync_inventory",
        new=AsyncMock(return_value=True),
    ) as mocked:
        summary = stock_transfer_service.sync_marketplace_listings(
            db=db, transfer_id=transfer.id
        )

    mocked.assert_not_called()
    assert summary["updated"] == []
    assert summary["missing_listings"] == [
        {"product_id": product.id, "qty_to_publish": 8}
    ]


def test_sync_listings_short_circuits_when_credential_needs_reauth(db, test_admin_user):
    """
    When the user's credential is marked needs_reauthorization, the sync
    must NOT call the connector — it should surface the reauth state on
    the response and on each affected listing's sync_status.
    """
    from src.crud.crud_marketplace_credential import (
        marketplace_credential as crud_cred,
    )
    from src.schemas.marketplace_credential import MarketplaceCredentialCreate

    product = _make_product(db, "MP-REAUTH")
    _seed_internal_stock(db, product.id, 30)
    mp = _ensure_marketplace(db)

    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=mp.id,
        external_listing_id="MLM-REAUTH-1",
        status="active",
        sync_status="SYNCED",
    )
    db.add(listing)

    # Seed a credential already marked for reauth.
    cred = crud_cred.create_with_owner(
        db,
        obj_in=MarketplaceCredentialCreate(
            marketplace_id=mp.id,
            access_token="stale",
            refresh_token="dead",
        ),
        user_id=test_admin_user.id,
    )
    cred.needs_reauthorization = True
    cred.last_refresh_error = "previous refresh denied"
    db.commit()

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location=LOCATION_ML_FULL,
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=12)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=12)],
    )

    with patch(
        "src.services.marketplaces.mercadolibre.MercadoLibreConnector.sync_inventory",
        new=AsyncMock(return_value=True),
    ) as mocked_sync:
        summary = stock_transfer_service.sync_marketplace_listings(
            db=db, transfer_id=transfer.id, user=test_admin_user
        )

    # Connector should not have been called because the credential is dead.
    mocked_sync.assert_not_called()
    assert summary["needs_reauthorization"] is True
    assert "previous refresh denied" in (summary["reauthorization_reason"] or "")
    assert summary["updated"][0]["error"] == "needs_reauthorization"
    assert summary["updated"][0]["ok"] is False

    db.refresh(listing)
    assert listing.sync_status == "ERROR"
    assert "Reauthorization required" in listing.error_message


def test_sync_listings_rejects_non_marketplace_destination(db):
    product = _make_product(db, "MP-SYNC-OTHER")
    _seed_internal_stock(db, product.id, 10)

    transfer = stock_transfer_service.create_draft(
        db=db,
        transfer_in=StockTransferCreate(
            dest_location="other-warehouse",
            items=[StockTransferItemCreate(product_id=product.id, qty_planned=4)],
        ),
    )
    stock_transfer_service.ship(db=db, transfer_id=transfer.id)
    stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer.id,
        received_items=[StockTransferReceiveItem(product_id=product.id, quantity=4)],
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        stock_transfer_service.sync_marketplace_listings(
            db=db, transfer_id=transfer.id
        )
    assert exc.value.status_code == 400
