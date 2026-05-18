"""
Coverage for `services/amazon_order_ingestion.py` and the
`tasks.poll_amazon_orders` Celery wrapper.

The service is exercised against the real test database (not a mock
session) so the SalesOrder / SalesOrderItem / InventoryItem writes are
verified end-to-end, and the cursor advancement is observable on the
credential row.

The Amazon connector itself is mocked at the method level — the
connector's own URL/params/pagination are covered by
`test_amazon_connector.py`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
)
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.services.amazon_order_ingestion import (
    AmazonOrderIngestionService,
    poll_all_amazon_credentials,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def amazon_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
        db.add(mp)
        db.commit()
        db.refresh(mp)
    return mp


@pytest.fixture
def amazon_credential(
    db: Session, amazon_marketplace: Marketplace, test_admin_user
) -> MarketplaceCredential:
    cred = MarketplaceCredential(
        user_id=test_admin_user.id,
        marketplace_id=amazon_marketplace.id,
        access_token="STUB-AMAZON-ACCESS",
        refresh_token="STUB-AMAZON-REFRESH",
        token_type="bearer",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


@pytest.fixture
def linked_product(
    db: Session, amazon_marketplace: Marketplace
) -> tuple[Product, MarketplaceListing]:
    """A product mapped to an Amazon listing by ASIN. Used by the
    inventory-decrement test to verify `_resolve_product_id` resolves
    `ASIN` → `marketplace_listings.external_listing_id` → `product_id`.
    """
    product = Product(
        name="Linked Amazon Product",
        sku="LINK-001",
        cost_price=10.0,
        default_resale_price=50.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()
    db.add(InventoryItem(product_id=product.id, quantity=10, location="default"))
    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=amazon_marketplace.id,
        external_listing_id="B000LINKED01",  # ASIN
        sync_status="IN_SYNC",
    )
    db.add(listing)
    db.commit()
    return product, listing


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


def _make_connector(orders, items_by_order=None):
    """Build a MagicMock AmazonConnector whose async methods return the
    given canned payloads. items_by_order maps AmazonOrderId → items."""
    connector = MagicMock()
    connector.fetch_orders = AsyncMock(return_value=orders)

    async def _items_side_effect(order_id, access_token=None):
        return (items_by_order or {}).get(order_id, [])

    connector.fetch_order_items = AsyncMock(side_effect=_items_side_effect)
    return connector


async def _run(service, db, credential, connector, *, now=None):
    return await service.ingest_for_credential(
        db, credential, connector, access_token="LIVE-TOKEN", now=now,
    )


@pytest.mark.anyio
async def test_creates_sales_order_and_items_and_decrements_inventory(
    db, amazon_credential, linked_product
):
    """A fresh AmazonOrderId → new SalesOrder + SalesOrderItem rows
    + inventory adjustment for the linked product."""
    product, _ = linked_product
    orders = [{
        "AmazonOrderId": "111-2222222-3333333",
        "PurchaseDate": "2026-05-17T10:00:00Z",
        "OrderStatus": "Shipped",
        "OrderTotal": {"CurrencyCode": "MXN", "Amount": "199.00"},
    }]
    items = {
        "111-2222222-3333333": [{
            "ASIN": "B000LINKED01",
            "SellerSKU": "LINK-001",
            "OrderItemId": "OI-1",
            "QuantityOrdered": 3,
            "ItemPrice": {"CurrencyCode": "MXN", "Amount": "199.00"},
        }],
    }
    connector = _make_connector(orders, items)

    summary = await _run(
        AmazonOrderIngestionService(), db, amazon_credential, connector,
        now=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    db.commit()

    assert summary == {"orders_new": 1, "orders_updated": 0, "orders_skipped": 0, "items_created": 1}

    sales_order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.source == OrderSource.AMAZON,
            SalesOrder.external_order_id == "111-2222222-3333333",
        )
        .one()
    )
    assert sales_order.status == "SHIPPED"
    assert sales_order.total_price == 199.0
    # PurchaseDate parsed and normalized to naive UTC
    assert sales_order.created_at == datetime(2026, 5, 17, 10, 0, 0)

    items_rows = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order.id).all()
    )
    assert len(items_rows) == 1
    assert items_rows[0].product_id == product.id
    assert items_rows[0].quantity == 3
    assert items_rows[0].price_per_unit == 199.0

    # Inventory: linked product had 10, order was for 3 → 7 remaining
    stock = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()
    assert stock.quantity == 7


@pytest.mark.anyio
async def test_existing_order_updates_status_only_and_does_not_redecrement(
    db, amazon_credential, linked_product
):
    """A re-poll of an order Fulcrum already saw must update status/total
    but not create new SalesOrderItem rows or decrement inventory again
    — same idempotency contract the ML webhook upholds."""
    product, _ = linked_product
    initial = SalesOrder(
        status="PENDING",
        total_price=100.0,
        created_at=datetime(2026, 5, 17, 10, 0, 0),
        source=OrderSource.AMAZON,
        external_order_id="111-9999999-9999999",
    )
    db.add(initial)
    db.flush()
    db.add(SalesOrderItem(
        order_id=initial.id, product_id=product.id, quantity=2, price_per_unit=50.0,
    ))
    db.commit()

    orders = [{
        "AmazonOrderId": "111-9999999-9999999",
        "PurchaseDate": "2026-05-17T10:00:00Z",
        "OrderStatus": "Shipped",
        "OrderTotal": {"CurrencyCode": "MXN", "Amount": "199.00"},
    }]
    connector = _make_connector(orders, {"111-9999999-9999999": [{
        # If the service tried to re-create items, this would show up.
        "ASIN": "B000LINKED01", "QuantityOrdered": 99,
    }]})

    summary = await _run(AmazonOrderIngestionService(), db, amazon_credential, connector)
    db.commit()

    assert summary["orders_updated"] == 1
    assert summary["orders_new"] == 0
    assert summary["items_created"] == 0

    sales_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.external_order_id == "111-9999999-9999999")
        .one()
    )
    assert sales_order.status == "SHIPPED"
    assert sales_order.total_price == 199.0

    # No second SalesOrderItem row was created.
    item_rows = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order.id).all()
    )
    assert len(item_rows) == 1

    # Inventory unchanged from its starting value (linked_product fixture
    # set it to 10; first ingestion didn't run, so still 10).
    stock = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()
    assert stock.quantity == 10

    # fetch_order_items should not have been called at all for the
    # existing-order path — the service hits SP-API only for new orders.
    connector.fetch_order_items.assert_not_awaited()


@pytest.mark.anyio
async def test_line_item_without_linked_product_creates_orphan_row_no_inventory_delta(
    db, amazon_credential
):
    """A SellerSKU/ASIN that doesn't map to a Fulcrum product still
    creates a SalesOrderItem row (with product_id=NULL) so the
    accountant's revenue total stays correct. Inventory is not touched."""
    orders = [{
        "AmazonOrderId": "ORPHAN-1",
        "PurchaseDate": "2026-05-17T10:00:00Z",
        "OrderStatus": "Pending",
        "OrderTotal": {"CurrencyCode": "MXN", "Amount": "9.99"},
    }]
    items = {"ORPHAN-1": [{
        "ASIN": "B000NOTMAPPED",
        "SellerSKU": "NOT-MAPPED",
        "QuantityOrdered": 1,
        "ItemPrice": {"CurrencyCode": "MXN", "Amount": "9.99"},
    }]}
    connector = _make_connector(orders, items)

    summary = await _run(AmazonOrderIngestionService(), db, amazon_credential, connector)
    db.commit()

    assert summary == {"orders_new": 1, "orders_updated": 0, "orders_skipped": 0, "items_created": 1}
    sales_order = (
        db.query(SalesOrder).filter(SalesOrder.external_order_id == "ORPHAN-1").one()
    )
    item_row = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order.id).one()
    )
    assert item_row.product_id is None
    assert item_row.quantity == 1
    assert item_row.price_per_unit == 9.99


@pytest.mark.anyio
async def test_uses_credential_cursor_as_created_after_then_advances_to_now(
    db, amazon_credential
):
    """Subsequent run: last_orders_polled_at is used as fetch_orders'
    created_after, and is advanced to the supplied `now` after the run.
    Verifies the delta-only-polling contract."""
    cursor_before = datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc)
    amazon_credential.last_orders_polled_at = cursor_before
    db.commit()

    connector = _make_connector(orders=[])
    now_marker = datetime(2026, 5, 18, 12, 30, 0, tzinfo=timezone.utc)

    summary = await _run(
        AmazonOrderIngestionService(), db, amazon_credential, connector, now=now_marker,
    )
    db.commit()

    connector.fetch_orders.assert_awaited_once()
    kwargs = connector.fetch_orders.await_args.kwargs
    assert kwargs["created_after"] == cursor_before
    assert kwargs["access_token"] == "LIVE-TOKEN"

    # Cursor advanced to the wall-clock supplied for the run.
    db.refresh(amazon_credential)
    assert amazon_credential.last_orders_polled_at == now_marker

    # Nothing to do for an empty page — summary all zeros, no items
    # fetched.
    assert summary == {"orders_new": 0, "orders_updated": 0, "orders_skipped": 0, "items_created": 0}
    connector.fetch_order_items.assert_not_awaited()


@pytest.mark.anyio
async def test_first_poll_with_null_cursor_passes_none_so_connector_uses_24h_default(
    db, amazon_credential
):
    """First poll for a credential: last_orders_polled_at is NULL, so
    we pass `created_after=None` and let AmazonConnector.fetch_orders
    pick its 24h default lookback."""
    assert amazon_credential.last_orders_polled_at is None
    connector = _make_connector(orders=[])

    await _run(AmazonOrderIngestionService(), db, amazon_credential, connector,
               now=datetime(2026, 5, 18, 0, 0, 0, tzinfo=timezone.utc))

    kwargs = connector.fetch_orders.await_args.kwargs
    assert kwargs["created_after"] is None


@pytest.mark.anyio
async def test_orders_without_amazon_order_id_are_skipped(
    db, amazon_credential
):
    """Defensive: an Orders payload missing AmazonOrderId (shouldn't
    happen in practice but SP-API has surprised us before) is counted
    as skipped, not crashed-on."""
    connector = _make_connector(orders=[{"OrderStatus": "Pending"}])

    summary = await _run(AmazonOrderIngestionService(), db, amazon_credential, connector)
    db.commit()

    assert summary == {"orders_new": 0, "orders_updated": 0, "orders_skipped": 1, "items_created": 0}
    assert db.query(SalesOrder).filter(SalesOrder.source == OrderSource.AMAZON).count() == 0


# ---------------------------------------------------------------------------
# poll_all_amazon_credentials — the synchronous wrapper Celery hits
# ---------------------------------------------------------------------------


def test_poll_all_amazon_credentials_filters_by_marketplace_and_health(
    db, amazon_marketplace, test_admin_user
):
    """Only credentials whose marketplace is "Amazon" (case-insensitive),
    `needs_reauthorization=False`, and have both tokens get polled. ML
    creds + reauth-required Amazon creds + token-less Amazon creds are
    all skipped."""
    # Healthy Amazon credential — should be picked up.
    healthy = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    # Needs-reauthorization Amazon credential — should be skipped.
    reauth = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
        needs_reauthorization=True,
    )
    # Tokenless — also skipped.
    tokenless = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token=None, refresh_token=None,
    )
    # MercadoLibre credential — different marketplace, skipped.
    ml = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db.add(ml)
    db.flush()
    ml_cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=ml.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add_all([healthy, reauth, tokenless, ml_cred])
    db.commit()

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.amazon_order_ingestion.amazon_order_ingestion.ingest_for_credential",
            new=AsyncMock(return_value={"orders_new": 0, "orders_updated": 0, "orders_skipped": 0, "items_created": 0}),
        ) as mock_ingest,
    ):
        results = poll_all_amazon_credentials(db)

    # Only the healthy Amazon credential was polled.
    assert list(results.keys()) == [healthy.id]
    assert mock_ingest.await_count == 1
    called_cred = mock_ingest.await_args.args[1]
    assert called_cred.id == healthy.id


def test_poll_all_amazon_credentials_keeps_loop_alive_on_per_credential_failure(
    db, amazon_marketplace, test_admin_user
):
    """A raise inside one credential's ingest call must NOT kill the
    Celery beat tick. Subsequent credentials still get processed; the
    failing one shows up in `results` with an "error" key."""
    cred_a = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    cred_b = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add_all([cred_a, cred_b])
    db.commit()

    call_count = {"n": 0}

    async def _ingest_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated SP-API outage")
        return {"orders_new": 0, "orders_updated": 0, "orders_skipped": 0, "items_created": 0}

    with (
        patch(
            "src.services.marketplace_service.marketplace_service.get_valid_access_token",
            new=AsyncMock(return_value="LIVE-TOKEN"),
        ),
        patch(
            "src.services.amazon_order_ingestion.amazon_order_ingestion.ingest_for_credential",
            new=AsyncMock(side_effect=_ingest_side_effect),
        ),
    ):
        results = poll_all_amazon_credentials(db)

    # Both credentials are represented; the first surfaces an error,
    # the second a summary.
    assert set(results.keys()) == {cred_a.id, cred_b.id}
    errored = [cid for cid, r in results.items() if "error" in r]
    succeeded = [cid for cid, r in results.items() if "error" not in r]
    assert len(errored) == 1
    assert len(succeeded) == 1


def test_poll_all_amazon_credentials_marks_reauth_required_without_raising(
    db, amazon_marketplace, test_admin_user
):
    """A credential whose `get_valid_access_token` raises
    `ReauthorizationRequiredError` lands in `results` with
    `{"error": "needs_reauthorization"}` — operator can grep for that
    string to spot stale creds — and the loop keeps running."""
    from src.services.marketplace_service import ReauthorizationRequiredError

    cred = MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=amazon_marketplace.id,
        access_token="STUB-A", refresh_token="STUB-R",
    )
    db.add(cred)
    db.commit()

    with patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        new=AsyncMock(side_effect=ReauthorizationRequiredError(
            credential_id=cred.id,
            marketplace_name="amazon",
            reason="invalid_grant",
        )),
    ):
        results = poll_all_amazon_credentials(db)

    assert results == {cred.id: {"error": "needs_reauthorization"}}


# ---------------------------------------------------------------------------
# Celery task wiring
# ---------------------------------------------------------------------------


def test_celery_task_is_registered_and_scheduled():
    """The beat schedule must point at the registered task name. A typo
    in either side would silently mean Beat fires nothing — easy to
    miss without an explicit test."""
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401 — register the task

    assert "src.tasks.poll_amazon_orders" in celery_app.tasks

    schedule = celery_app.conf.beat_schedule
    assert "amazon-order-poll" in schedule
    assert schedule["amazon-order-poll"]["task"] == "src.tasks.poll_amazon_orders"


def test_celery_task_delegates_to_poll_all_amazon_credentials():
    """The Celery wrapper opens a SessionLocal, calls
    `poll_all_amazon_credentials(db)`, and returns its result. Verifies
    we don't accidentally bypass the session lifecycle when changing
    the wrapper."""
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)

    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.amazon_order_ingestion.poll_all_amazon_credentials",
            return_value={"sentinel": True},
        ) as mock_poll,
    ):
        result = task_module.poll_amazon_orders()

    assert result == {"sentinel": True}
    mock_poll.assert_called_once_with(fake_session)
    fake_session.close.assert_called_once()
