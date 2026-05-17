import pytest
from unittest.mock import AsyncMock, patch
from src.services.marketplaces.amazon import AmazonConnector, MEXICO_MARKETPLACE_ID

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


# ---------------------------------------------------------------------------
# fetch_all_listings
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_all_listings_calls_sp_api_with_mexico_marketplace():
    """Happy path: one SP-API page, two items. Verifies URL, headers,
    query params (marketplaceIds=MEXICO + includedData=summaries,offers),
    and that the response parser pulls asin/itemName/price into the
    canonical ListingData shape."""
    connector = AmazonConnector()
    sp_api_body = {
        "items": [
            {
                "sku": "SKU-A",
                "summaries": [
                    {
                        "marketplaceId": MEXICO_MARKETPLACE_ID,
                        "asin": "B000111111",
                        "itemName": "Item Alpha",
                        "status": ["BUYABLE"],
                    },
                ],
                "offers": [
                    {"price": {"amount": "199.00", "currencyCode": "MXN"}},
                ],
            },
            {
                "sku": "SKU-B",
                "summaries": [
                    {
                        "marketplaceId": MEXICO_MARKETPLACE_ID,
                        "asin": "B000222222",
                        "itemName": "Item Beta",
                        "status": ["DISCOVERABLE"],
                    },
                ],
                "offers": [],
            },
        ],
        "pagination": {},
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: sp_api_body,
            raise_for_status=lambda: None,
        )
        with patch("src.config.settings.AMAZON_SELLER_ID", "SELLER123"):
            listings = await connector.fetch_all_listings(access_token="LIVE-TOKEN")

    assert mock_get.call_count == 1
    args, kwargs = mock_get.call_args
    assert args[0] == f"{connector.api_base_url}/listings/2021-08-01/items/SELLER123"
    assert kwargs["headers"]["x-amz-access-token"] == "LIVE-TOKEN"
    assert kwargs["params"]["marketplaceIds"] == MEXICO_MARKETPLACE_ID
    assert kwargs["params"]["includedData"] == "summaries,offers"
    assert "pageToken" not in kwargs["params"]  # first page

    assert len(listings) == 2
    assert listings[0].external_id == "B000111111"
    assert listings[0].sku == "SKU-A"
    assert listings[0].title == "Item Alpha"
    assert listings[0].price == 199.0
    assert listings[0].currency == "MXN"
    assert listings[0].status == "BUYABLE"
    # Second item has no offers — price/currency should fall through cleanly
    assert listings[1].external_id == "B000222222"
    assert listings[1].price is None
    assert listings[1].currency == "MXN"  # default when no offer present
    assert listings[1].status == "DISCOVERABLE"


@pytest.mark.anyio
async def test_fetch_all_listings_paginates_via_next_token():
    """Two-page response: page 1 returns nextToken, page 2 returns
    empty nextToken. Verifies the loop concatenates results and passes
    pageToken on the second request."""
    connector = AmazonConnector()
    page1 = {
        "items": [{"sku": "P1-1", "summaries": [{"marketplaceId": MEXICO_MARKETPLACE_ID, "asin": "A1", "itemName": "P1-1"}]}],
        "pagination": {"nextToken": "TOKEN-PAGE-2"},
    }
    page2 = {
        "items": [{"sku": "P2-1", "summaries": [{"marketplaceId": MEXICO_MARKETPLACE_ID, "asin": "A2", "itemName": "P2-1"}]}],
        "pagination": {},  # no nextToken → stop
    }
    responses = iter([page1, page2])

    def _make_response(*args, **kwargs):
        body = next(responses)
        return AsyncMock(status_code=200, json=lambda b=body: b, raise_for_status=lambda: None)

    with patch("httpx.AsyncClient.get", side_effect=_make_response) as mock_get:
        with patch("src.config.settings.AMAZON_SELLER_ID", "SELLER123"):
            listings = await connector.fetch_all_listings(access_token="LIVE-TOKEN")

    assert mock_get.call_count == 2
    # First call: no pageToken
    assert "pageToken" not in mock_get.call_args_list[0].kwargs["params"]
    # Second call: pageToken=TOKEN-PAGE-2
    assert mock_get.call_args_list[1].kwargs["params"]["pageToken"] == "TOKEN-PAGE-2"
    # Both pages' items concatenated
    assert [li.external_id for li in listings] == ["A1", "A2"]


@pytest.mark.anyio
async def test_fetch_all_listings_returns_stub_without_token():
    """Dev convenience: no access_token → return one stub listing without
    hitting the network. Mirrors publish_listing's stub branch so the
    Marketplaces page renders in a fresh dev workspace."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.get") as mock_get:
        listings = await connector.fetch_all_listings(access_token=None)

    mock_get.assert_not_called()
    assert len(listings) == 1
    assert listings[0].external_id == "AMZ-STUB-ASIN-001"
    assert listings[0].sku == "STUB-SKU-001"


@pytest.mark.anyio
async def test_fetch_all_listings_returns_stub_for_stub_prefixed_token():
    """Same stub behaviour for tokens that start with STUB- (the
    convention publish_listing already uses for seeded dev credentials)."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.get") as mock_get:
        listings = await connector.fetch_all_listings(access_token="STUB-AMAZON-TOKEN")

    mock_get.assert_not_called()
    assert len(listings) == 1
    assert listings[0].external_id == "AMZ-STUB-ASIN-001"


@pytest.mark.anyio
async def test_fetch_all_listings_skips_no_offers_gracefully():
    """A listing with no offers or no summaries is common (e.g. items
    that were deleted on Amazon's side or have no buy box). The parser
    must not crash — it should produce a minimal ListingData with
    null/empty defaults."""
    connector = AmazonConnector()
    sp_api_body = {
        "items": [
            {"sku": "BROKEN-SKU", "summaries": [], "offers": []},
        ],
        "pagination": {},
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: sp_api_body,
            raise_for_status=lambda: None,
        )
        listings = await connector.fetch_all_listings(access_token="LIVE-TOKEN")

    assert len(listings) == 1
    assert listings[0].sku == "BROKEN-SKU"
    # Falls back to sku when no asin
    assert listings[0].external_id == "BROKEN-SKU"
    assert listings[0].title == ""
    assert listings[0].price is None
    assert listings[0].status == "ACTIVE"  # default fallback
