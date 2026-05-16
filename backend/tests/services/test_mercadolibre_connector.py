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
