import pytest
from unittest.mock import AsyncMock, patch

from src.services.marketplaces.mercadolibre import MercadoLibreConnector


@pytest.mark.anyio
async def test_sync_inventory_puts_to_items_endpoint():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.put") as mock_put:
        mock_put.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"id": "MLM123", "available_quantity": 42},
            raise_for_status=lambda: None,
        )

        ok = await connector.sync_inventory("MLM123", 42, access_token="ML-TOKEN")

    assert ok is True
    assert mock_put.call_count == 1
    args, kwargs = mock_put.call_args
    assert args[0] == "https://api.mercadolibre.com/items/MLM123"
    assert kwargs["json"] == {"available_quantity": 42}
    assert kwargs["headers"]["Authorization"] == "Bearer ML-TOKEN"


@pytest.mark.anyio
async def test_sync_inventory_returns_false_without_token():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.put") as mock_put:
        ok = await connector.sync_inventory("MLM123", 42, access_token=None)

    assert ok is False
    mock_put.assert_not_called()


@pytest.mark.anyio
async def test_sync_price_puts_to_items_endpoint():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.put") as mock_put:
        mock_put.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"id": "MLM123", "price": 199.99},
            raise_for_status=lambda: None,
        )

        ok = await connector.sync_price("MLM123", 199.99, access_token="ML-TOKEN")

    assert ok is True
    assert mock_put.call_count == 1
    args, kwargs = mock_put.call_args
    assert args[0] == "https://api.mercadolibre.com/items/MLM123"
    assert kwargs["json"] == {"price": 199.99}
    assert kwargs["headers"]["Authorization"] == "Bearer ML-TOKEN"


@pytest.mark.anyio
async def test_sync_price_returns_false_without_token():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.put") as mock_put:
        ok = await connector.sync_price("MLM123", 199.99, access_token=None)

    assert ok is False
    mock_put.assert_not_called()


@pytest.mark.anyio
async def test_publish_listing_posts_to_items_with_mexico_defaults():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=201,
            json=lambda: {"id": "MLM999000111", "status": "active"},
            raise_for_status=lambda: None,
        )

        external_id = await connector.publish_listing(
            {
                "name": "Test Widget",
                "sku": "WIDGET-1",
                "description": "A widget for testing.",
                "price": 199.99,
            },
            access_token="ML-TOKEN",
        )

    assert external_id == "MLM999000111"
    assert mock_post.call_count == 1
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.mercadolibre.com/items"
    assert kwargs["headers"]["Authorization"] == "Bearer ML-TOKEN"

    sent = kwargs["json"]
    assert sent["site_id"] == "MLM"
    assert sent["title"] == "Test Widget"
    assert sent["price"] == 199.99
    assert sent["currency_id"] == "MXN"
    assert sent["available_quantity"] == 1
    assert sent["buying_mode"] == "buy_it_now"
    assert sent["listing_type_id"] == "gold_special"
    assert sent["condition"] == "new"
    assert sent["description"] == {"plain_text": "A widget for testing."}
    # category_id wasn't provided and is intentionally not defaulted (it
    # would need to be a real MLM category id), so it must be absent.
    assert "category_id" not in sent
    # pictures weren't provided
    assert "pictures" not in sent


@pytest.mark.anyio
async def test_publish_listing_allows_caller_overrides():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=201,
            json=lambda: {"id": "MLM222"},
            raise_for_status=lambda: None,
        )

        await connector.publish_listing(
            {
                "title": "Explicit Title",
                "price": 49.0,
                "currency_id": "USD",
                "available_quantity": 25,
                "condition": "used",
                "category_id": "MLM1051",
                "listing_type_id": "free",
                "pictures": [{"source": "https://example.test/image.jpg"}],
                "description": "Used widget.",
            },
            access_token="ML-TOKEN",
        )

    sent = mock_post.call_args.kwargs["json"]
    assert sent["title"] == "Explicit Title"
    assert sent["currency_id"] == "USD"
    assert sent["available_quantity"] == 25
    assert sent["condition"] == "used"
    assert sent["category_id"] == "MLM1051"
    assert sent["listing_type_id"] == "free"
    assert sent["pictures"] == [{"source": "https://example.test/image.jpg"}]


@pytest.mark.anyio
async def test_publish_listing_returns_stub_without_token():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.post") as mock_post:
        external_id = await connector.publish_listing(
            {"name": "Stub Widget", "sku": "STUB-001"},
            access_token=None,
        )

    assert external_id == "MLM-STUB-STUB-001"
    mock_post.assert_not_called()


@pytest.mark.anyio
async def test_publish_listing_returns_stub_for_stub_token():
    connector = MercadoLibreConnector()

    with patch("httpx.AsyncClient.post") as mock_post:
        external_id = await connector.publish_listing(
            {"name": "Stub Widget", "sku": "STUB-002"},
            access_token="STUB-TOKEN",
        )

    assert external_id == "MLM-STUB-STUB-002"
    mock_post.assert_not_called()
