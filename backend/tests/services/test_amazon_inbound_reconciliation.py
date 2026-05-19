"""
Coverage for the Amazon FBA inbound-reconciliation surface:

1. `AmazonConnector.get_inbound_shipment_status` parses SP-API's
   two-call response shape (shipment status doc + paginated items
   endpoint) into the marketplace-agnostic `InboundShipmentResult`.
2. The SKU-fallback resolution path in
   `inbound_shipment_reconciliation` correctly maps a SellerSKU back
   to a local Product when no MarketplaceListing matches.
3. The Amazon bulk runner (`reconcile_all_open_amazon_inbounds`)
   filters by `dest_location='amazon-fba'` and uses the same per-
   transfer SAVEPOINT isolation the ML runner does.
4. The Celery task wrapper + beat schedule entry are wired.

The ML-side semantics are covered by
`test_inbound_shipment_reconciliation.py`; this file only exercises
the Amazon-specific glue.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

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
from src.services.inbound_shipment_reconciliation import (
    InboundShipmentReconciliationService,
    reconcile_all_open_amazon_inbounds,
)
from src.services.marketplaces.amazon import AmazonConnector
from src.services.marketplaces.base import (
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)


# ---------------------------------------------------------------------------
# AmazonConnector.get_inbound_shipment_status — parsing-level coverage
# ---------------------------------------------------------------------------


def test_get_inbound_shipment_status_stub_branch_without_token():
    """No access token → returns a stub `pending` result without
    hitting SP-API. Mirrors the other Amazon connector methods'
    stub-token convention so dev/test envs don't need live creds."""
    connector = AmazonConnector()
    result = asyncio.run(connector.get_inbound_shipment_status("FBA-123"))
    assert result.external_inbound_id == "FBA-123"
    assert result.status == "pending"
    assert result.received_items == []
    assert result.raw_data.get("stub") is True


def test_get_inbound_shipment_status_stub_branch_with_stub_token():
    """A `STUB-` access token also short-circuits to the stub branch
    — same convention as fetch_orders / fetch_all_listings."""
    connector = AmazonConnector()
    result = asyncio.run(
        connector.get_inbound_shipment_status("FBA-X", access_token="STUB-TOKEN")
    )
    assert result.status == "pending"
    assert result.received_items == []


def test_get_inbound_shipment_status_parses_two_call_sp_api_shape(monkeypatch):
    """Real call: SP-API splits the response across two endpoints.
    Stub `httpx.AsyncClient.get` to return a shipment doc + an items
    page, and verify the connector folds them into the canonical
    `InboundShipmentResult`."""
    connector = AmazonConnector()

    shipment_payload = {
        "payload": {
            "InboundShipmentData": {
                "ShipmentId": "FBA-REAL-1",
                "ShipmentStatus": "RECEIVING",
            }
        }
    }
    items_payload = {
        "payload": {
            "ItemData": [
                {"SellerSKU": "AMZN-SKU-A", "QuantityShipped": 10, "QuantityReceived": 7},
                # `QuantityReceived` returned as a string — defensive coercion.
                {"SellerSKU": "AMZN-SKU-B", "QuantityShipped": 5, "QuantityReceived": "3"},
                # Missing the field entirely → coerces to 0, not a crash.
                {"SellerSKU": "AMZN-SKU-C", "QuantityShipped": 2},
            ],
        }
    }
    captured_requests: list[httpx.Request] = []

    async def _fake_get(self, url, headers=None, params=None):
        # `Response.raise_for_status()` needs a `request` attribute or
        # it raises RuntimeError. Build a real Request object so the
        # response behaves like one from a normal AsyncClient round-trip.
        req = httpx.Request("GET", url, params=params, headers=headers)
        captured_requests.append(req)
        if "items" in url:
            payload = items_payload
        else:
            payload = shipment_payload
        return httpx.Response(200, json=payload, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    result = asyncio.run(
        connector.get_inbound_shipment_status(
            "FBA-REAL-1", access_token="LIVE-AMZ-TOKEN",
        )
    )

    assert result.external_inbound_id == "FBA-REAL-1"
    assert result.status == "receiving"  # lowercased for parity with ML
    by_sku = {r.external_listing_id: r.received_quantity for r in result.received_items}
    assert by_sku == {
        "AMZN-SKU-A": 7,
        "AMZN-SKU-B": 3,
        "AMZN-SKU-C": 0,
    }
    # Both fields populated with SellerSKU so the resolution path can
    # use listing-id OR sku without per-marketplace branching.
    for r in result.received_items:
        assert r.external_listing_id == r.sku


def test_get_inbound_shipment_status_paginates_items_endpoint(monkeypatch):
    """SP-API's items endpoint paginates with `NextToken`. The
    connector must follow it until exhausted; otherwise large
    shipments would silently lose late items."""
    connector = AmazonConnector()

    shipment_payload = {"payload": {"InboundShipmentInfo": {"ShipmentStatus": "RECEIVING"}}}
    items_page_1 = {
        "payload": {
            "ItemData": [
                {"SellerSKU": "P1", "QuantityReceived": 1},
                {"SellerSKU": "P2", "QuantityReceived": 2},
            ],
            "NextToken": "token-page-2",
        }
    }
    items_page_2 = {
        "payload": {
            "ItemData": [{"SellerSKU": "P3", "QuantityReceived": 3}],
            # No NextToken → loop terminates after this page.
        }
    }
    pages = [shipment_payload, items_page_1, items_page_2]

    async def _fake_get(self, url, headers=None, params=None):
        req = httpx.Request("GET", url, params=params, headers=headers)
        return httpx.Response(200, json=pages.pop(0), request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    result = asyncio.run(
        connector.get_inbound_shipment_status("FBA-X", access_token="LIVE"),
    )
    skus = [r.external_listing_id for r in result.received_items]
    assert skus == ["P1", "P2", "P3"]


# ---------------------------------------------------------------------------
# Reconciliation service: SKU fallback path (Amazon's primary lookup mode)
# ---------------------------------------------------------------------------


pytestmark = pytest.mark.db


@pytest.fixture
def amazon_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


def _make_product(db, sku):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Amzn Inbound {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _make_listing_by_asin(db, marketplace_id, product_id, asin):
    listing = MarketplaceListing(
        product_id=product_id,
        marketplace_id=marketplace_id,
        external_listing_id=asin,
        sync_status="IN_SYNC",
    )
    db.add(listing)
    db.commit()
    return listing


def _make_shipped_transfer(
    db,
    *,
    items,
    external_inbound_id="FBA-INBOUND-1",
    dest_location=LOCATION_AMAZON_FBA,
    created_by_id=None,
):
    transfer = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location=dest_location,
        status=StockTransferStatus.SHIPPED.value,
        external_inbound_id=external_inbound_id,
        created_by_id=created_by_id,
    )
    db.add(transfer)
    db.flush()
    for product_id, qty in items:
        db.add(StockTransferItem(
            transfer_id=transfer.id,
            product_id=product_id,
            qty_planned=qty,
            qty_shipped=qty,
            qty_received=0,
        ))
    db.commit()
    db.refresh(transfer)
    return transfer


@pytest.mark.anyio
async def test_amazon_sku_fallback_resolves_when_listing_uses_asin(
    db, amazon_marketplace, test_admin_user,
):
    """The crucial Amazon-specific path: SP-API's FBA inbound items
    endpoint reports `SellerSKU`, but Amazon `MarketplaceListing` rows
    are typically keyed by ASIN (the `_parse_listing_item` primary
    branch). The reconciliation service's SKU fallback must catch
    this and still credit the right product."""
    product = _make_product(db, "AMZN-FALLBACK-1")
    # Listing intentionally uses ASIN (not the SKU) as
    # external_listing_id, mirroring the typical Amazon listing import.
    _make_listing_by_asin(db, amazon_marketplace.id, product.id, "B0000ASIN01")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 8)], created_by_id=test_admin_user.id,
    )

    connector = MagicMock()
    connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="FBA-INBOUND-1",
            status="receiving",
            received_items=[
                # SellerSKU reported in BOTH fields, as the connector
                # actually emits. The MarketplaceListing lookup will
                # MISS (since listings use ASIN); the SKU fallback
                # picks up Product.sku == "AMZN-FALLBACK-1".
                InboundShipmentReceivedItem(
                    external_listing_id="AMZN-FALLBACK-1",
                    sku="AMZN-FALLBACK-1",
                    received_quantity=5,
                ),
            ],
        ),
    )

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=amazon_marketplace.id,
        actor="amazon-inbound-poll",
    )
    db.commit()

    assert summary["items_updated"] == 1
    assert summary["total_received_added"] == 5
    assert transfer.items[0].qty_received == 5
    assert transfer.status == StockTransferStatus.PARTIALLY_RECEIVED.value

    fba_stock = db.query(InventoryItem).filter(
        InventoryItem.product_id == product.id,
        InventoryItem.location == LOCATION_AMAZON_FBA,
    ).one()
    assert fba_stock.quantity == 5


@pytest.mark.anyio
async def test_reconcile_bumps_last_reconciled_at_even_when_no_delta(
    db, amazon_marketplace, test_admin_user,
):
    """Idempotent reconciliation still advances `last_reconciled_at`
    so the UI can show "Reconciled X ago" even when nothing changed.
    Operators need to know the poll ran, not just whether it updated
    anything."""
    product = _make_product(db, "AMZN-TICK-1")
    _make_listing_by_asin(db, amazon_marketplace.id, product.id, "B0000ASIN02")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 5)], created_by_id=test_admin_user.id,
    )
    assert transfer.last_reconciled_at is None

    connector = MagicMock()
    connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="FBA-INBOUND-1",
            status="working",
            received_items=[],  # nothing received yet
        ),
    )

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=amazon_marketplace.id,
    )
    db.commit()

    assert summary["items_updated"] == 0
    db.refresh(transfer)
    assert transfer.last_reconciled_at is not None


# ---------------------------------------------------------------------------
# Bulk runner — Amazon-specific filtering + isolation
# ---------------------------------------------------------------------------


def test_amazon_bulk_runner_only_polls_amazon_fba_transfers(
    db, amazon_marketplace, test_admin_user,
):
    """A mixed environment with both ML and Amazon open transfers must
    only see the Amazon ones through `reconcile_all_open_amazon_inbounds`.
    Guards against the bulk runner accidentally cross-polling ML
    transfers under the Amazon connector."""
    amzn_product = _make_product(db, "BULK-AMZN")
    _make_listing_by_asin(db, amazon_marketplace.id, amzn_product.id, "B-ASIN-BULK")
    amzn_cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(amzn_cred)
    db.commit()
    amzn_transfer = _make_shipped_transfer(
        db, items=[(amzn_product.id, 3)],
        external_inbound_id="FBA-RUN-1",
        dest_location=LOCATION_AMAZON_FBA,
        created_by_id=test_admin_user.id,
    )

    # Set up an ML transfer that must be invisible to the Amazon runner.
    ml = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db.add(ml)
    db.flush()
    ml_product = _make_product(db, "BULK-ML")
    ml_listing = MarketplaceListing(
        product_id=ml_product.id, marketplace_id=ml.id,
        external_listing_id="MLM-BULK", sync_status="IN_SYNC",
    )
    db.add(ml_listing)
    db.flush()
    ml_transfer = _make_shipped_transfer(
        db, items=[(ml_product.id, 5)],
        external_inbound_id="MLM-RUN-1",
        dest_location=LOCATION_ML_FULL,
        created_by_id=test_admin_user.id,
    )

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="FBA-RUN-1",
            status="receiving",
            received_items=[InboundShipmentReceivedItem(
                external_listing_id="BULK-AMZN", sku="BULK-AMZN",
                received_quantity=3,
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
        results = reconcile_all_open_amazon_inbounds(db)

    # The Amazon transfer is the only one in the results dict; the ML
    # transfer is invisible to this runner.
    assert list(results.keys()) == [amzn_transfer.id]
    assert ml_transfer.id not in results
    assert results[amzn_transfer.id]["items_updated"] == 1


# ---------------------------------------------------------------------------
# Celery task wiring
# ---------------------------------------------------------------------------


def test_amazon_celery_task_is_registered_and_scheduled():
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401 — register task

    assert "src.tasks.reconcile_amazon_inbound_shipments" in celery_app.tasks
    schedule = celery_app.conf.beat_schedule
    assert "amazon-inbound-reconcile" in schedule
    assert (
        schedule["amazon-inbound-reconcile"]["task"]
        == "src.tasks.reconcile_amazon_inbound_shipments"
    )


def test_amazon_celery_task_delegates_to_bulk_runner():
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)
    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.inbound_shipment_reconciliation.reconcile_all_open_amazon_inbounds",
            return_value={"sentinel": True},
        ) as mock_runner,
    ):
        result = task_module.reconcile_amazon_inbound_shipments()
    assert result == {"sentinel": True}
    mock_runner.assert_called_once_with(fake_session)
    fake_session.close.assert_called_once()
