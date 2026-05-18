"""
Coverage for `services/inbound_shipment_reconciliation.py` —
back-fills `qty_received` on `StockTransferItem` rows from a
marketplace's reported inbound-shipment state.

Today the only marketplace wired up is MercadoLibre. The service is
exercised against the real test DB so `inventory_items` writes and
`qty_received` mutations are verified end-to-end.

The ML connector's `get_inbound_shipment_status` is mocked at the
method level — its own HTTP + parsing is covered by
`test_ml_inbound_shipment.py` and `test_mercadolibre_connector.py`.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.schemas.product import ProductCreate
from src.services.marketplaces.base import (
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)
from src.services.inbound_shipment_reconciliation import (
    InboundShipmentReconciliationService,
    reconcile_all_open_ml_inbounds,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def ml_marketplace(db: Session) -> Marketplace:
    mp = (
        db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    )
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


@pytest.fixture
def ml_credential(
    db: Session, ml_marketplace: Marketplace, test_admin_user
) -> MarketplaceCredential:
    cred = MarketplaceCredential(
        user_id=test_admin_user.id,
        marketplace_id=ml_marketplace.id,
        access_token="STUB-ML-ACCESS",
        refresh_token="STUB-ML-REFRESH",
        token_type="bearer",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def _make_product(db, sku):
    return crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Inbound {sku}",
            sku=sku,
            default_resale_price=20.0,
            cost_price=10.0,
        ),
    )


def _make_listing(db, marketplace_id, product_id, external_listing_id):
    listing = MarketplaceListing(
        product_id=product_id,
        marketplace_id=marketplace_id,
        external_listing_id=external_listing_id,
        sync_status="IN_SYNC",
    )
    db.add(listing)
    db.commit()
    return listing


def _make_shipped_transfer(
    db,
    *,
    items,
    external_inbound_id="ML-INBOUND-1",
    created_by_id=None,
):
    """Insert a transfer in SHIPPED state with the given (product_id,
    qty_shipped) pairs. Skips the service's ship() flow so tests don't
    need to seed internal stock first."""
    transfer = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location=LOCATION_ML_FULL,
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


def _make_connector(received_items, status="receiving"):
    """Build a MagicMock connector that returns a canned status poll."""
    connector = MagicMock()
    connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="ML-INBOUND-1",
            status=status,
            received_items=received_items,
        )
    )
    return connector


# ---------------------------------------------------------------------------
# Single-transfer reconciliation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_partial_receipt_advances_qty_received_and_status_and_credits_dest_stock(
    db, ml_marketplace, test_admin_user,
):
    """ML reports 6/10 received → local qty_received becomes 6, stock
    at `ml-full` increases by 6, status advances to
    PARTIALLY_RECEIVED."""
    product = _make_product(db, "SKU-A")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-A")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 10)], created_by_id=test_admin_user.id,
    )

    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-A", received_quantity=6),
    ])

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    assert summary["items_updated"] == 1
    assert summary["total_received_added"] == 6
    assert summary["status_before"] == StockTransferStatus.SHIPPED.value
    assert summary["status_after"] == StockTransferStatus.PARTIALLY_RECEIVED.value

    db.refresh(transfer)
    assert transfer.status == StockTransferStatus.PARTIALLY_RECEIVED.value
    item = transfer.items[0]
    assert item.qty_received == 6

    ml_stock = db.query(InventoryItem).filter(
        InventoryItem.product_id == product.id,
        InventoryItem.location == LOCATION_ML_FULL,
    ).one()
    assert ml_stock.quantity == 6


@pytest.mark.anyio
async def test_full_receipt_advances_status_to_received_and_sets_received_at(
    db, ml_marketplace, test_admin_user,
):
    """ML reports the full shipped quantity → status RECEIVED + a
    received_at timestamp is set."""
    product = _make_product(db, "SKU-B")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-B")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 5)], created_by_id=test_admin_user.id,
    )

    connector = _make_connector(
        received_items=[
            InboundShipmentReceivedItem(external_listing_id="MLM-B", received_quantity=5),
        ],
        status="received",
    )

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    assert summary["status_after"] == StockTransferStatus.RECEIVED.value
    db.refresh(transfer)
    assert transfer.status == StockTransferStatus.RECEIVED.value
    assert transfer.received_at is not None


@pytest.mark.anyio
async def test_idempotent_when_no_marketplace_state_change(
    db, ml_marketplace, test_admin_user,
):
    """Two reconciliation calls with the same marketplace state — the
    second is a no-op. Guards against double-crediting stock if the
    Celery beat fires twice before something else changes."""
    product = _make_product(db, "SKU-C")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-C")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 10)], created_by_id=test_admin_user.id,
    )
    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-C", received_quantity=4),
    ])

    service = InboundShipmentReconciliationService()
    await service.reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    summary_2 = await service.reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    assert summary_2["items_updated"] == 0
    assert summary_2["total_received_added"] == 0

    item = transfer.items[0]
    assert item.qty_received == 4  # not 8
    ml_stock = db.query(InventoryItem).filter(
        InventoryItem.product_id == product.id,
        InventoryItem.location == LOCATION_ML_FULL,
    ).one()
    assert ml_stock.quantity == 4  # still 4


@pytest.mark.anyio
async def test_marketplace_over_reporting_is_capped_at_qty_shipped(
    db, ml_marketplace, test_admin_user,
):
    """If ML reports MORE received than we shipped (warehouse error or
    cross-ship of another seller's units), we cap at shipped. The
    delta beyond shipped is NOT credited to local stock."""
    product = _make_product(db, "SKU-D")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-D")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 3)], created_by_id=test_admin_user.id,
    )
    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-D", received_quantity=99),
    ])

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    assert summary["total_received_added"] == 3
    assert transfer.items[0].qty_received == 3
    assert transfer.status == StockTransferStatus.RECEIVED.value


@pytest.mark.anyio
async def test_unmapped_listing_is_recorded_not_crashed_on(
    db, ml_marketplace, test_admin_user,
):
    """ML reports a listing id we have no local mapping for — the
    reconciliation records it in `unmapped_listings` and continues
    processing the other items in the same poll."""
    mapped = _make_product(db, "SKU-E1")
    _make_listing(db, ml_marketplace.id, mapped.id, "MLM-E1")
    transfer = _make_shipped_transfer(
        db, items=[(mapped.id, 5)], created_by_id=test_admin_user.id,
    )
    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-E1", received_quantity=2),
        InboundShipmentReceivedItem(external_listing_id="MLM-GHOST", received_quantity=1),
    ])

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    db.commit()

    assert summary["items_updated"] == 1
    assert summary.get("unmapped_listings") == ["MLM-GHOST"]
    assert transfer.items[0].qty_received == 2


@pytest.mark.anyio
async def test_skips_when_transfer_has_no_external_inbound_id(
    db, ml_marketplace, test_admin_user,
):
    """A transfer marked SHIPPED without a marketplace inbound id (e.g.
    operator chose the manual receive workflow) is skipped so the
    poller doesn't error trying to query nothing."""
    product = _make_product(db, "SKU-F")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-F")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 5)],
        external_inbound_id=None,
        created_by_id=test_admin_user.id,
    )
    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-F", received_quantity=2),
    ])

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    assert summary["skipped_reason"] == "no_external_inbound_id"
    assert summary["items_updated"] == 0
    connector.get_inbound_shipment_status.assert_not_awaited()


@pytest.mark.anyio
async def test_skips_when_transfer_is_in_terminal_state(
    db, ml_marketplace, test_admin_user,
):
    """A transfer already in RECEIVED / CANCELLED isn't polled. We
    only ever advance OPEN transfers."""
    product = _make_product(db, "SKU-G")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-G")
    transfer = _make_shipped_transfer(
        db, items=[(product.id, 5)], created_by_id=test_admin_user.id,
    )
    transfer.status = StockTransferStatus.RECEIVED.value
    db.commit()

    connector = _make_connector(received_items=[
        InboundShipmentReceivedItem(external_listing_id="MLM-G", received_quantity=5),
    ])

    summary = await InboundShipmentReconciliationService().reconcile_for_transfer(
        db, transfer, connector, access_token="LIVE",
        marketplace_id=ml_marketplace.id,
    )
    assert summary["skipped_reason"].startswith("status_")
    connector.get_inbound_shipment_status.assert_not_awaited()


# ---------------------------------------------------------------------------
# Bulk runner — what the Celery beat task calls
# ---------------------------------------------------------------------------


def test_bulk_runner_skips_transfer_without_credential_and_keeps_going(
    db, ml_marketplace, test_admin_user,
):
    """Transfer #1 has a created_by_id with no ML credential and
    `created_by_id=None` falls back to "any healthy credential". When
    neither path finds one, the transfer is recorded with
    `error=no_credential` and the loop continues to the next one."""
    product_a = _make_product(db, "SKU-BULK-A")
    product_b = _make_product(db, "SKU-BULK-B")
    _make_listing(db, ml_marketplace.id, product_a.id, "MLM-BA")
    _make_listing(db, ml_marketplace.id, product_b.id, "MLM-BB")

    # Transfer A: created_by_id=None and no credential exists at all.
    transfer_a = _make_shipped_transfer(
        db, items=[(product_a.id, 5)],
        external_inbound_id="ML-INBOUND-A",
        created_by_id=None,
    )
    # Transfer B: has a credential (created via the fixture below).
    cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()
    transfer_b = _make_shipped_transfer(
        db, items=[(product_b.id, 5)],
        external_inbound_id="ML-INBOUND-B",
        created_by_id=test_admin_user.id,
    )

    # Mock the connector to "receive" 5/5 on transfer B's listing.
    async def _status(external_id, access_token=None):
        return InboundShipmentResult(
            external_inbound_id=external_id,
            status="received",
            received_items=[InboundShipmentReceivedItem(
                external_listing_id="MLM-BB", received_quantity=5,
            )],
        )

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(side_effect=_status)

    # Detach the first credential temporarily so transfer A's fallback
    # path returns None. We do this by ALSO simulating a state where
    # `_ml_credential_for_transfer` returns None for transfer A —
    # easiest path is to delete the credential before A is processed.
    # Since the bulk runner orders by transfer id, A is processed
    # first; we delete the credential AFTER the connector lookup but
    # BEFORE the runner queries it. The cleanest test is to never
    # create the credential before this point — but transfer B needs
    # one. So we patch _ml_credential_for_transfer to return None for
    # A and the real credential for B.
    from src.services import inbound_shipment_reconciliation as recon_mod
    original = recon_mod._ml_credential_for_transfer

    def _stub_cred(db_arg, transfer, ml_id):
        if transfer.id == transfer_a.id:
            return None
        return original(db_arg, transfer, ml_id)

    with (
        patch.object(recon_mod, "_ml_credential_for_transfer", new=_stub_cred),
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.marketplace_service.marketplace_service.get_connector",
            return_value=fake_connector,
        ),
    ):
        results = reconcile_all_open_ml_inbounds(db)

    assert results[transfer_a.id] == {"error": "no_credential"}
    assert results[transfer_b.id]["items_updated"] == 1


def test_bulk_runner_keeps_loop_alive_on_per_transfer_failure(
    db, ml_marketplace, test_admin_user,
):
    """One bad transfer's exception must NOT kill the rest of the
    Celery tick. Errored transfer surfaces with `error=exception`."""
    product_a = _make_product(db, "SKU-BULKE-A")
    product_b = _make_product(db, "SKU-BULKE-B")
    _make_listing(db, ml_marketplace.id, product_a.id, "MLM-EA")
    _make_listing(db, ml_marketplace.id, product_b.id, "MLM-EB")
    cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()
    transfer_a = _make_shipped_transfer(
        db, items=[(product_a.id, 5)],
        external_inbound_id="ML-INBOUND-A",
        created_by_id=test_admin_user.id,
    )
    transfer_b = _make_shipped_transfer(
        db, items=[(product_b.id, 5)],
        external_inbound_id="ML-INBOUND-B",
        created_by_id=test_admin_user.id,
    )

    call_count = {"n": 0}

    async def _status(external_id, access_token=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated ML API outage")
        return InboundShipmentResult(
            external_inbound_id=external_id,
            status="receiving",
            received_items=[InboundShipmentReceivedItem(
                external_listing_id="MLM-EB", received_quantity=2,
            )],
        )

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(side_effect=_status)

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
        results = reconcile_all_open_ml_inbounds(db)

    assert results[transfer_a.id] == {"error": "exception"}
    assert results[transfer_b.id]["items_updated"] == 1


def test_bulk_runner_only_polls_open_ml_transfers_with_inbound_id(
    db, ml_marketplace, test_admin_user,
):
    """Filtering contract:
      - DRAFT / RECEIVED / CANCELLED transfers are NOT polled.
      - SHIPPED / PARTIALLY_RECEIVED transfers ARE polled.
      - Transfers whose `dest_location` is not `ml-full` are skipped.
      - Transfers with NULL `external_inbound_id` are skipped.
    """
    product = _make_product(db, "SKU-FILTER")
    _make_listing(db, ml_marketplace.id, product.id, "MLM-FILTER")
    cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()

    # Eligible:
    eligible = _make_shipped_transfer(
        db, items=[(product.id, 5)],
        external_inbound_id="ML-OK",
        created_by_id=test_admin_user.id,
    )
    # Not eligible — DRAFT
    draft = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location=LOCATION_ML_FULL,
        status=StockTransferStatus.DRAFT.value,
        external_inbound_id="ML-DRAFT",
        created_by_id=test_admin_user.id,
    )
    # Not eligible — NULL external_inbound_id
    no_inbound = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location=LOCATION_ML_FULL,
        status=StockTransferStatus.SHIPPED.value,
        external_inbound_id=None,
        created_by_id=test_admin_user.id,
    )
    # Not eligible — wrong destination
    other_dest = StockTransfer(
        source_location=LOCATION_INTERNAL,
        dest_location="amazon-fba",
        status=StockTransferStatus.SHIPPED.value,
        external_inbound_id="FBA-OK",
        created_by_id=test_admin_user.id,
    )
    db.add_all([draft, no_inbound, other_dest])
    db.commit()

    fake_connector = MagicMock()
    fake_connector.get_inbound_shipment_status = AsyncMock(
        return_value=InboundShipmentResult(
            external_inbound_id="ML-OK",
            status="receiving",
            received_items=[],
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
        results = reconcile_all_open_ml_inbounds(db)

    # Only the eligible transfer is in the results dict.
    assert list(results.keys()) == [eligible.id]
    assert fake_connector.get_inbound_shipment_status.await_count == 1


# ---------------------------------------------------------------------------
# Celery task wiring
# ---------------------------------------------------------------------------


def test_celery_task_is_registered_and_scheduled():
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401 — register the task

    assert "src.tasks.reconcile_ml_inbound_shipments" in celery_app.tasks
    schedule = celery_app.conf.beat_schedule
    assert "mercadolibre-inbound-reconcile" in schedule
    assert (
        schedule["mercadolibre-inbound-reconcile"]["task"]
        == "src.tasks.reconcile_ml_inbound_shipments"
    )


def test_celery_task_delegates_to_bulk_runner():
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)
    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.inbound_shipment_reconciliation.reconcile_all_open_ml_inbounds",
            return_value={"sentinel": True},
        ) as mock_runner,
    ):
        result = task_module.reconcile_ml_inbound_shipments()
    assert result == {"sentinel": True}
    mock_runner.assert_called_once_with(fake_session)
    fake_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Connector-level: per-item parsing of ML's inbound status payload
# ---------------------------------------------------------------------------


def test_connector_parses_received_items_with_aliased_keys():
    """ML has used several key names across API revisions:
    `received_quantity`, `quantity_received`, plain `quantity`. The
    connector must accept all three and fall back to 0 for missing.
    """
    from src.services.marketplaces.mercadolibre import MercadoLibreConnector

    sample = {
        "status": "receiving",
        "items": [
            {"item_id": "MLM-1", "received_quantity": 4},
            {"item_id": "MLM-2", "quantity_received": 7},
            {"item_id": "MLM-3", "quantity": 1},
            {"item_id": "MLM-4"},  # no qty key at all → 0
        ],
    }
    parsed = MercadoLibreConnector._parse_received_items(sample)
    by_id = {p.external_listing_id: p.received_quantity for p in parsed}
    assert by_id == {"MLM-1": 4, "MLM-2": 7, "MLM-3": 1, "MLM-4": 0}
