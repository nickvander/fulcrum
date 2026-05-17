"""
End-to-end coverage for the MercadoLibre webhook -> SalesOrder pipeline.

Exercises process_mercadolibre_event against a realistic order payload:
- the ML connector + access token are mocked (no live HTTP),
- the function's own SessionLocal is patched to return a session bound to
  the test's connection so commits join the test transaction,
- assertions cover SalesOrder + SalesOrderItem creation, InventoryItem
  decrement, and the WebhookEvent state transition to PROCESSED.
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session, sessionmaker

from src.api.v1.endpoints.webhooks import process_mercadolibre_event
from src.models.inventory import InventoryItem
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
    WebhookEvent,
)
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product


def _seed_ml_marketplace(db: Session) -> tuple[Marketplace, MarketplaceCredential, Product, MarketplaceListing]:
    marketplace = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
    db.add(marketplace)
    db.flush()

    credential = MarketplaceCredential(
        marketplace_id=marketplace.id,
        access_token="fake-encrypted-token",
        refresh_token="fake-encrypted-refresh",
    )
    db.add(credential)

    product = Product(
        name="ML Widget",
        sku="ML-WIDGET-E2E",
        default_resale_price=199.99,
        cost_price=100.0,
        is_bundle=False,
    )
    db.add(product)
    db.flush()

    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=marketplace.id,
        external_listing_id="MLM999",
        status="active",
        sync_status="SYNCED",
    )
    db.add(listing)

    return marketplace, credential, product, listing


def _patched_session_local(db: Session):
    """
    Return a SessionLocal stand-in that builds sessions on the test's
    connection. Commits in process_mercadolibre_event will join the test's
    outer transaction so the fixture rollback still cleans up.
    """
    connection = db.connection()
    factory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    return factory


@pytest.mark.db
@pytest.mark.anyio
async def test_ml_order_webhook_creates_sales_order_and_decrements_stock(db: Session):
    marketplace, _credential, product, _listing = _seed_ml_marketplace(db)

    inventory = InventoryItem(
        product_id=product.id,
        variant_id=None,
        quantity=10,
        location="default",
    )
    db.add(inventory)

    event = WebhookEvent(
        marketplace_id=marketplace.id,
        topic="orders",
        external_resource_id="/orders/123456",
        payload={"resource": "/orders/123456", "topic": "orders"},
        status="RECEIVED",
    )
    db.add(event)
    db.commit()
    event_id = event.id

    ml_order_payload = {
        "id": 123456,
        "status": "paid",
        "total_amount": 399.98,
        "date_created": "2026-05-16T12:00:00.000Z",
        "order_items": [
            {
                "item": {"id": "MLM999", "title": "ML Widget"},
                "quantity": 2,
                "unit_price": 199.99,
            }
        ],
    }

    mock_connector = AsyncMock()
    mock_connector.fetch_order = AsyncMock(return_value=ml_order_payload)

    with patch(
        "src.api.v1.endpoints.webhooks.SessionLocal",
        new=_patched_session_local(db),
    ), patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        new=AsyncMock(return_value="resolved-bearer"),
    ), patch(
        "src.services.marketplace_service.marketplace_service.get_connector",
        return_value=mock_connector,
    ):
        await process_mercadolibre_event(event_id)

    db.expire_all()

    sales_order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.source == OrderSource.MERCADOLIBRE,
            SalesOrder.external_order_id == "123456",
        )
        .first()
    )
    assert sales_order is not None
    assert sales_order.status == "PAID"
    assert sales_order.total_price == pytest.approx(399.98)

    items = (
        db.query(SalesOrderItem)
        .filter(SalesOrderItem.order_id == sales_order.id)
        .all()
    )
    assert len(items) == 1
    assert items[0].product_id == product.id
    assert items[0].quantity == 2
    assert items[0].price_per_unit == pytest.approx(199.99)

    decremented = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product.id)
        .first()
    )
    assert decremented is not None
    assert decremented.quantity == 8

    refreshed_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    assert refreshed_event is not None
    assert refreshed_event.status == "PROCESSED"
    assert refreshed_event.processed_at is not None
    mock_connector.fetch_order.assert_awaited_once_with("123456", "resolved-bearer")


@pytest.mark.db
@pytest.mark.anyio
async def test_ml_non_order_topic_is_marked_processed_without_fetch(db: Session):
    marketplace, _credential, _product, _listing = _seed_ml_marketplace(db)

    event = WebhookEvent(
        marketplace_id=marketplace.id,
        topic="items",
        external_resource_id="/items/MLM999",
        payload={"resource": "/items/MLM999", "topic": "items"},
        status="RECEIVED",
    )
    db.add(event)
    db.commit()
    event_id = event.id

    mock_connector = AsyncMock()

    with patch(
        "src.api.v1.endpoints.webhooks.SessionLocal",
        new=_patched_session_local(db),
    ), patch(
        "src.services.marketplace_service.marketplace_service.get_connector",
        return_value=mock_connector,
    ):
        await process_mercadolibre_event(event_id)

    db.expire_all()
    refreshed_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    assert refreshed_event.status == "PROCESSED"
    mock_connector.fetch_order.assert_not_called()


@pytest.mark.db
@pytest.mark.anyio
async def test_ml_duplicate_order_updates_status_without_double_decrement(db: Session):
    marketplace, _credential, product, _listing = _seed_ml_marketplace(db)

    inventory = InventoryItem(
        product_id=product.id,
        variant_id=None,
        quantity=10,
        location="default",
    )
    db.add(inventory)

    # An earlier webhook already created the SalesOrder + decremented stock.
    prior_order = SalesOrder(
        status="PAID",
        total_price=199.99,
        source=OrderSource.MERCADOLIBRE,
        external_order_id="999",
    )
    db.add(prior_order)
    db.flush()
    db.add(
        SalesOrderItem(
            order_id=prior_order.id,
            product_id=product.id,
            quantity=1,
            price_per_unit=199.99,
        )
    )
    inventory.quantity = 9  # simulate the prior decrement

    event = WebhookEvent(
        marketplace_id=marketplace.id,
        topic="orders",
        external_resource_id="/orders/999",
        payload={"resource": "/orders/999", "topic": "orders"},
        status="RECEIVED",
    )
    db.add(event)
    db.commit()
    event_id = event.id

    refreshed_payload = {
        "id": 999,
        "status": "shipped",  # status moved on
        "total_amount": 199.99,
        "date_created": "2026-05-16T12:00:00.000Z",
        "order_items": [
            {
                "item": {"id": "MLM999"},
                "quantity": 1,
                "unit_price": 199.99,
            }
        ],
    }

    mock_connector = AsyncMock()
    mock_connector.fetch_order = AsyncMock(return_value=refreshed_payload)

    with patch(
        "src.api.v1.endpoints.webhooks.SessionLocal",
        new=_patched_session_local(db),
    ), patch(
        "src.services.marketplace_service.marketplace_service.get_valid_access_token",
        new=AsyncMock(return_value="resolved-bearer"),
    ), patch(
        "src.services.marketplace_service.marketplace_service.get_connector",
        return_value=mock_connector,
    ):
        await process_mercadolibre_event(event_id)

    db.expire_all()
    updated_order = (
        db.query(SalesOrder)
        .filter(SalesOrder.external_order_id == "999")
        .first()
    )
    assert updated_order.status == "SHIPPED"

    # Stock should still be 9 (not 8) — the duplicate webhook must not double-decrement.
    inventory_after = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product.id)
        .first()
    )
    assert inventory_after.quantity == 9
