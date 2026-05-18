"""
Coverage for `services/mercadolibre_order_ingestion.py` and the
`tasks.poll_mercadolibre_orders` Celery wrapper.

Same shape as `test_amazon_order_ingestion.py`: the service is
exercised against a real test DB (not a mocked session) so that
SalesOrder/SalesOrderItem/InventoryItem writes + cursor advancement
are verified end-to-end. The ML connector is mocked at the method
level — `fetch_orders` is the only seam the service depends on, and
the connector's own URL/auth/pagination is covered separately in
`test_mercadolibre_connector.py`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
)
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.services.mercadolibre_order_ingestion import (
    MercadoLibreOrderIngestionService,
    poll_all_mercadolibre_credentials,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixtures
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


@pytest.fixture
def linked_product(
    db: Session, ml_marketplace: Marketplace
) -> tuple[Product, MarketplaceListing]:
    """Product mapped to an ML listing by item id. Verifies that
    `find_local_product_id` resolves ML's `item.id` →
    `marketplace_listings.external_listing_id` → `product_id`."""
    product = Product(
        name="Linked ML Product",
        sku="ML-LINK-001",
        cost_price=10.0,
        default_resale_price=50.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()
    db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=ml_marketplace.id,
        external_listing_id="MLM123LINKED",
        sync_status="IN_SYNC",
    )
    db.add(listing)
    db.commit()
    return product, listing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connector(orders):
    connector = MagicMock()
    connector.fetch_orders = AsyncMock(return_value=orders)
    return connector


async def _run(service, db, credential, connector, *, now=None):
    return await service.ingest_for_credential(
        db, credential, connector, access_token="LIVE-TOKEN", now=now,
    )


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_creates_sales_order_and_items_and_decrements_inventory(
    db, ml_credential, linked_product
):
    """A fresh ML order id → new SalesOrder + SalesOrderItem rows +
    inventory adjustment for the linked product. Mirrors the same
    semantics the ML webhook handler upholds."""
    product, _ = linked_product
    orders = [{
        "id": 2000000001,
        "date_created": "2026-05-17T10:00:00.000Z",
        "status": "paid",
        "total_amount": 199.0,
        "order_items": [{
            "quantity": 3,
            "unit_price": 199.0,
            "item": {"id": "MLM123LINKED"},
        }],
    }]
    connector = _make_connector(orders)

    summary = await _run(
        MercadoLibreOrderIngestionService(), db, ml_credential, connector,
        now=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    db.commit()

    assert summary == {
        "orders_new": 1,
        "orders_updated": 0,
        "orders_skipped": 0,
        "items_created": 1,
    }

    sales_order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.source == OrderSource.MERCADOLIBRE,
            SalesOrder.external_order_id == "2000000001",
        )
        .one()
    )
    # Status normalized to UPPER like the webhook handler does.
    assert sales_order.status == "PAID"
    assert sales_order.total_price == 199.0
    assert sales_order.created_at == datetime(2026, 5, 17, 10, 0, 0)

    items_rows = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order.id).all()
    )
    assert len(items_rows) == 1
    assert items_rows[0].product_id == product.id
    assert items_rows[0].quantity == 3
    assert items_rows[0].price_per_unit == 199.0
    # Cost-at-sale captured from current Product.cost_price.
    assert items_rows[0].cost_per_unit == 10.0

    stock = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()
    assert stock.quantity == 7
    # The audit log records who did the adjustment so operators can
    # distinguish poll-driven decrements from webhook-driven ones.
    adj = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.product_id == product.id)
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )
    assert adj is not None
    assert adj.created_by == "mercadolibre-poll"


@pytest.mark.anyio
async def test_existing_order_updates_status_and_total_only_no_redecrement(
    db, ml_credential, linked_product
):
    """A re-poll of an order Fulcrum already has (e.g. arriving after
    the webhook handled it, or on the next 15-min tick) must NOT
    re-create line items or re-decrement stock. Status + total are
    refreshed in case ML's state advanced."""
    product, _ = linked_product
    initial = SalesOrder(
        status="PENDING",
        total_price=100.0,
        created_at=datetime(2026, 5, 17, 10, 0, 0),
        source=OrderSource.MERCADOLIBRE,
        external_order_id="2000000002",
    )
    db.add(initial)
    db.flush()
    db.add(SalesOrderItem(
        order_id=initial.id, product_id=product.id, quantity=2, price_per_unit=50.0,
    ))
    db.commit()

    orders = [{
        "id": 2000000002,
        "date_created": "2026-05-17T10:00:00.000Z",
        "status": "shipped",
        "total_amount": 199.0,
        "order_items": [{
            # Even if ML returns lines here, the existing-order branch
            # ignores them — otherwise we'd double-decrement stock on
            # every poll tick.
            "quantity": 99,
            "unit_price": 1.0,
            "item": {"id": "MLM123LINKED"},
        }],
    }]
    connector = _make_connector(orders)

    summary = await _run(
        MercadoLibreOrderIngestionService(), db, ml_credential, connector,
    )
    db.commit()

    assert summary == {
        "orders_new": 0, "orders_updated": 1, "orders_skipped": 0, "items_created": 0,
    }

    refreshed = (
        db.query(SalesOrder).filter(SalesOrder.external_order_id == "2000000002").one()
    )
    assert refreshed.status == "SHIPPED"
    assert refreshed.total_price == 199.0

    items_rows = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == refreshed.id).all()
    )
    assert len(items_rows) == 1  # No second row.

    stock = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()
    assert stock.quantity == 10  # Unchanged.


@pytest.mark.anyio
async def test_line_item_without_linked_product_creates_orphan_row_no_inventory_delta(
    db, ml_credential
):
    """An ML item id that doesn't map to a Fulcrum product still
    creates a SalesOrderItem row (with product_id=NULL) so revenue
    totals stay correct. Inventory is not touched."""
    orders = [{
        "id": 2000000003,
        "date_created": "2026-05-17T10:00:00.000Z",
        "status": "paid",
        "total_amount": 9.99,
        "order_items": [{
            "quantity": 1,
            "unit_price": 9.99,
            "item": {"id": "MLM-NOT-MAPPED"},
        }],
    }]
    connector = _make_connector(orders)

    summary = await _run(
        MercadoLibreOrderIngestionService(), db, ml_credential, connector,
    )
    db.commit()

    assert summary == {
        "orders_new": 1, "orders_updated": 0, "orders_skipped": 0, "items_created": 1,
    }
    sales_order = (
        db.query(SalesOrder).filter(SalesOrder.external_order_id == "2000000003").one()
    )
    item_row = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order.id).one()
    )
    assert item_row.product_id is None
    assert item_row.quantity == 1
    assert item_row.price_per_unit == 9.99
    # Cost is NULL for orphan rows (margin SQL falls back to product cost
    # via COALESCE for legacy rows).
    assert item_row.cost_per_unit is None


@pytest.mark.anyio
async def test_uses_credential_cursor_as_created_from_then_advances_to_now(
    db, ml_credential
):
    """Subsequent run: `last_orders_polled_at` is passed as
    `created_from` to fetch_orders, and advanced to the run's `now` on
    success. This is the contract that makes delta-polling correct."""
    cursor_before = datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc)
    ml_credential.last_orders_polled_at = cursor_before
    db.commit()

    connector = _make_connector(orders=[])
    now_marker = datetime(2026, 5, 18, 12, 30, 0, tzinfo=timezone.utc)

    summary = await _run(
        MercadoLibreOrderIngestionService(), db, ml_credential, connector,
        now=now_marker,
    )
    db.commit()

    connector.fetch_orders.assert_awaited_once()
    kwargs = connector.fetch_orders.await_args.kwargs
    assert kwargs["created_from"] == cursor_before
    assert kwargs["access_token"] == "LIVE-TOKEN"

    db.refresh(ml_credential)
    assert ml_credential.last_orders_polled_at == now_marker

    assert summary == {
        "orders_new": 0, "orders_updated": 0, "orders_skipped": 0, "items_created": 0,
    }


@pytest.mark.anyio
async def test_first_poll_with_null_cursor_passes_none_so_connector_uses_24h_default(
    db, ml_credential
):
    """First poll for a credential: `last_orders_polled_at` is NULL, so
    we pass `created_from=None` and let
    `MercadoLibreConnector.fetch_orders` use its 24h fallback. That
    keeps the very first run bounded even if no migration has been run
    yet on a brand-new credential."""
    assert ml_credential.last_orders_polled_at is None
    connector = _make_connector(orders=[])

    await _run(MercadoLibreOrderIngestionService(), db, ml_credential, connector,
               now=datetime(2026, 5, 18, 0, 0, 0, tzinfo=timezone.utc))

    kwargs = connector.fetch_orders.await_args.kwargs
    assert kwargs["created_from"] is None


@pytest.mark.anyio
async def test_orders_without_id_are_skipped_not_crashed_on(
    db, ml_credential
):
    """Defensive: an ML order payload missing `id` (shouldn't happen in
    prod but ML has surprised us before) is counted as skipped, not
    raised. Other orders in the same batch still process."""
    connector = _make_connector(orders=[
        {"status": "paid", "total_amount": 1.0},
        {"id": 2000000004, "status": "paid", "total_amount": 5.0, "order_items": []},
    ])

    summary = await _run(
        MercadoLibreOrderIngestionService(), db, ml_credential, connector,
    )
    db.commit()

    assert summary == {
        "orders_new": 1, "orders_updated": 0, "orders_skipped": 1, "items_created": 0,
    }


@pytest.mark.anyio
async def test_paid_amount_fallback_when_total_amount_missing(db, ml_credential):
    """ML sometimes returns `paid_amount` without `total_amount` for
    pending-payment orders. The mapper falls back so the SalesOrder row
    still has a useful price column."""
    orders = [{
        "id": 2000000005,
        "date_created": "2026-05-17T10:00:00.000Z",
        "status": "paid",
        "paid_amount": 88.0,  # `total_amount` deliberately absent.
        "order_items": [],
    }]
    connector = _make_connector(orders)

    await _run(MercadoLibreOrderIngestionService(), db, ml_credential, connector)
    db.commit()

    so = (
        db.query(SalesOrder).filter(SalesOrder.external_order_id == "2000000005").one()
    )
    assert so.total_price == 88.0


# ---------------------------------------------------------------------------
# poll_all_mercadolibre_credentials — the synchronous Celery wrapper
# ---------------------------------------------------------------------------


def test_poll_all_filters_by_marketplace_and_health(
    db, ml_marketplace, test_admin_user
):
    """Only credentials whose marketplace is "MercadoLibre"
    (case-insensitive), `needs_reauthorization=False`, and have both
    tokens get polled. Amazon creds + reauth-required + token-less are
    all skipped — same filter contract as the Amazon poller."""
    healthy = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    reauth = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
        needs_reauthorization=True,
    )
    tokenless = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token=None, refresh_token=None,
    )
    amazon = Marketplace(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
    db.add(amazon)
    db.flush()
    amazon_cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add_all([healthy, reauth, tokenless, amazon_cred])
    db.commit()

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.mercadolibre_order_ingestion.mercadolibre_order_ingestion.ingest_for_credential",
            new=AsyncMock(return_value={
                "orders_new": 0, "orders_updated": 0,
                "orders_skipped": 0, "items_created": 0,
            }),
        ) as mock_ingest,
    ):
        results = poll_all_mercadolibre_credentials(db)

    assert list(results.keys()) == [healthy.id]
    assert mock_ingest.await_count == 1
    called_cred = mock_ingest.await_args.args[1]
    assert called_cred.id == healthy.id


def test_poll_all_keeps_loop_alive_on_per_credential_failure(
    db, ml_marketplace, test_admin_user
):
    """A raise inside one credential's ingest MUST NOT kill the Celery
    beat tick — same isolation guarantee as the Amazon poller."""
    cred_a = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    cred_b = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add_all([cred_a, cred_b])
    db.commit()

    call_count = {"n": 0}

    async def _ingest_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated ML API outage")
        return {
            "orders_new": 0, "orders_updated": 0,
            "orders_skipped": 0, "items_created": 0,
        }

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.mercadolibre_order_ingestion.mercadolibre_order_ingestion.ingest_for_credential",
            new=AsyncMock(side_effect=_ingest_side_effect),
        ),
    ):
        results = poll_all_mercadolibre_credentials(db)

    assert set(results.keys()) == {cred_a.id, cred_b.id}
    errored = [cid for cid, r in results.items() if "error" in r]
    succeeded = [cid for cid, r in results.items() if "error" not in r]
    assert len(errored) == 1
    assert len(succeeded) == 1


def test_poll_all_marks_reauth_required_without_raising(
    db, ml_marketplace, test_admin_user
):
    """A credential whose `get_valid_access_token` raises
    `ReauthorizationRequiredError` lands in `results` with
    `{"error": "needs_reauthorization"}` so an operator can grep for
    stale creds; the loop continues."""
    from src.services.marketplace_service import ReauthorizationRequiredError

    cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        new=AsyncMock(side_effect=ReauthorizationRequiredError(
            credential_id=cred.id,
            marketplace_name="mercadolibre",
            reason="invalid_grant",
        )),
    ):
        results = poll_all_mercadolibre_credentials(db)

    assert results == {cred.id: {"error": "needs_reauthorization"}}


# ---------------------------------------------------------------------------
# Celery task wiring
# ---------------------------------------------------------------------------


def test_celery_task_is_registered_and_scheduled():
    """The beat schedule entry must point at the registered task name.
    A typo on either side would mean Beat silently fires nothing."""
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401 — register the task

    assert "src.tasks.poll_mercadolibre_orders" in celery_app.tasks
    schedule = celery_app.conf.beat_schedule
    assert "mercadolibre-order-poll" in schedule
    assert schedule["mercadolibre-order-poll"]["task"] == "src.tasks.poll_mercadolibre_orders"


def test_celery_task_delegates_to_poll_all_mercadolibre_credentials():
    """The wrapper opens a SessionLocal, delegates to the synchronous
    poll function, and closes the session even on success."""
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)

    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.mercadolibre_order_ingestion.poll_all_mercadolibre_credentials",
            return_value={"sentinel": True},
        ) as mock_poll,
    ):
        result = task_module.poll_mercadolibre_orders()

    assert result == {"sentinel": True}
    mock_poll.assert_called_once_with(fake_session)
    fake_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Webhook ↔ poller shared helpers (regression guard for the helper-move
# refactor — webhooks.py imports `_ml_order_to_sales_order` and
# `_find_local_product_id` from the new service module).
# ---------------------------------------------------------------------------


def test_webhook_module_still_exposes_helpers_for_backwards_compatibility():
    """The helpers moved to the ingestion service, but `webhooks.py`
    re-exports them under their original private names so any external
    import still resolves. Guards against accidental deletion."""
    from src.api.v1.endpoints import webhooks

    assert callable(webhooks._ml_order_to_sales_order)
    assert callable(webhooks._find_local_product_id)
