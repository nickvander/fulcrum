import pytest
from unittest.mock import AsyncMock, patch
from src.services.marketplaces.amazon import AmazonConnector

@pytest.mark.db
@pytest.mark.anyio
async def test_amazon_get_auth_url():

    connector = AmazonConnector()
    with patch("src.config.settings.AMAZON_CLIENT_ID", "test-client-id"):
        url = await connector.get_auth_url()
        assert "application_id=test-client-id" in url
        assert "version=beta" in url

@pytest.mark.db
@pytest.mark.anyio
async def test_amazon_exchange_code():
    connector = AmazonConnector()
    mock_response = {
        "access_token": "Atzr|...",
        "refresh_token": "Atzr|...",
        "expires_in": 3600,
        "token_type": "bearer"
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        tokens = await connector.exchange_code_for_token("test-code")
        assert tokens["access_token"] == "Atzr|..."
        assert tokens["refresh_token"] == "Atzr|..."

@pytest.mark.db
@pytest.mark.anyio
async def test_amazon_refresh_token():
    connector = AmazonConnector()
    mock_response = {
        "access_token": "Atzr|new",
        "expires_in": 3600
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        tokens = await connector.refresh_token("old-refresh-token")
        assert tokens["access_token"] == "Atzr|new"
