from datetime import datetime, timezone

import httpx
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


# ---------------------------------------------------------------------------
# sync_inventory
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sync_inventory_patches_sp_api_with_marketplace_param():
    """Happy path: real token → PATCH /listings/2021-08-01/items/{seller}/{sku}
    with marketplaceIds query param + fulfillment_availability patch body."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.patch") as mock_patch:
        mock_patch.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "ACCEPTED"},
            raise_for_status=lambda: None,
        )
        with patch("src.config.settings.AMAZON_SELLER_ID", "SELLER123"):
            ok = await connector.sync_inventory("SKU-A", 42, access_token="LIVE-TOKEN")

    assert ok is True
    assert mock_patch.call_count == 1
    args, kwargs = mock_patch.call_args
    assert args[0] == f"{connector.api_base_url}/listings/2021-08-01/items/SELLER123/SKU-A"
    assert kwargs["headers"]["x-amz-access-token"] == "LIVE-TOKEN"
    # marketplaceIds is REQUIRED by SP-API on Listings writes — without
    # it the PATCH 400s.
    assert kwargs["params"]["marketplaceIds"] == MEXICO_MARKETPLACE_ID
    body = kwargs["json"]
    assert body["productType"] == "PRODUCT"
    patches = body["patches"]
    assert len(patches) == 1
    assert patches[0]["op"] == "replace"
    assert patches[0]["path"] == "/attributes/fulfillment_availability"
    assert patches[0]["value"] == [{"fulfillment_channel_code": "DEFAULT", "quantity": 42}]


@pytest.mark.anyio
async def test_sync_inventory_returns_true_without_hitting_api_for_stub_tokens():
    """No token / STUB-prefixed token → return True with zero network
    activity. Same convention as fetch_all_listings."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.patch") as mock_patch:
        ok_no_token = await connector.sync_inventory("SKU-A", 5, access_token=None)
        ok_stub = await connector.sync_inventory("SKU-A", 5, access_token="STUB-AMAZON")

    assert ok_no_token is True
    assert ok_stub is True
    mock_patch.assert_not_called()


@pytest.mark.anyio
async def test_sync_inventory_propagates_http_status_error_for_401_retry():
    """An SP-API 401 must propagate as httpx.HTTPStatusError so that
    MarketplaceService.call_with_401_retry can force-refresh the token
    and try again. The previous bare-except swallowed every error and
    silently returned True, which broke the retry wrapper."""
    connector = AmazonConnector()

    request = httpx.Request("PATCH", "https://example/listings/2021-08-01/items/X/Y")
    error_response = httpx.Response(status_code=401, request=request, text="unauthorized")

    def _raise():
        raise httpx.HTTPStatusError("unauthorized", request=request, response=error_response)

    with patch("httpx.AsyncClient.patch") as mock_patch:
        mock_patch.return_value = AsyncMock(
            status_code=401,
            raise_for_status=_raise,
        )
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await connector.sync_inventory("SKU-A", 1, access_token="LIVE-TOKEN")

    assert excinfo.value.response.status_code == 401


# ---------------------------------------------------------------------------
# fetch_orders
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_orders_calls_sp_api_with_marketplace_and_created_after():
    """Happy path: one SP-API page, two orders. Verifies URL, headers,
    required query params (MarketplaceIds + CreatedAfter), and that the
    raw payload.Orders list is returned untouched (the marketplace dict
    shape is the canonical return until a second consumer demands a
    structured type)."""
    connector = AmazonConnector()
    body = {
        "payload": {
            "Orders": [
                {
                    "AmazonOrderId": "111-2222222-3333333",
                    "PurchaseDate": "2026-05-17T10:00:00Z",
                    "OrderStatus": "Shipped",
                    "OrderTotal": {"CurrencyCode": "MXN", "Amount": "199.00"},
                    "MarketplaceId": MEXICO_MARKETPLACE_ID,
                },
                {
                    "AmazonOrderId": "444-5555555-6666666",
                    "PurchaseDate": "2026-05-17T11:00:00Z",
                    "OrderStatus": "Unshipped",
                    "OrderTotal": {"CurrencyCode": "MXN", "Amount": "49.50"},
                    "MarketplaceId": MEXICO_MARKETPLACE_ID,
                },
            ],
            # No NextToken → single page
        }
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: body,
            raise_for_status=lambda: None,
        )
        orders = await connector.fetch_orders(
            access_token="LIVE-TOKEN",
            created_after=datetime(2026, 5, 16, 10, 0, 0, tzinfo=timezone.utc),
        )

    assert mock_get.call_count == 1
    args, kwargs = mock_get.call_args
    assert args[0] == f"{connector.api_base_url}/orders/v0/orders"
    assert kwargs["headers"]["x-amz-access-token"] == "LIVE-TOKEN"
    assert kwargs["params"]["MarketplaceIds"] == MEXICO_MARKETPLACE_ID
    assert kwargs["params"]["CreatedAfter"] == "2026-05-16T10:00:00Z"
    assert "NextToken" not in kwargs["params"]

    assert [o["AmazonOrderId"] for o in orders] == [
        "111-2222222-3333333",
        "444-5555555-6666666",
    ]
    # Raw passthrough — caller can read the full SP-API shape.
    assert orders[0]["OrderTotal"]["Amount"] == "199.00"


@pytest.mark.anyio
async def test_fetch_orders_paginates_via_next_token():
    """Two-page response: page 1 has NextToken, page 2 returns no
    NextToken. Verifies the second call carries NextToken (and NOT
    CreatedAfter — SP-API rejects that combo) and that results
    concatenate."""
    connector = AmazonConnector()
    page1 = {
        "payload": {
            "Orders": [{"AmazonOrderId": "O1"}],
            "NextToken": "PAGE-2-TOKEN",
        }
    }
    page2 = {
        "payload": {
            "Orders": [{"AmazonOrderId": "O2"}],
        }
    }
    responses = iter([page1, page2])

    def _make_response(*args, **kwargs):
        b = next(responses)
        return AsyncMock(status_code=200, json=lambda body=b: body, raise_for_status=lambda: None)

    with patch("httpx.AsyncClient.get", side_effect=_make_response) as mock_get:
        orders = await connector.fetch_orders(
            access_token="LIVE-TOKEN",
            created_after=datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc),
        )

    assert mock_get.call_count == 2
    # First call: CreatedAfter, no NextToken
    first_params = mock_get.call_args_list[0].kwargs["params"]
    assert first_params["CreatedAfter"] == "2026-05-17T00:00:00Z"
    assert "NextToken" not in first_params
    # Second call: NextToken, NO CreatedAfter (SP-API rejects both
    # together once you're paginating).
    second_params = mock_get.call_args_list[1].kwargs["params"]
    assert second_params["NextToken"] == "PAGE-2-TOKEN"
    assert "CreatedAfter" not in second_params
    assert [o["AmazonOrderId"] for o in orders] == ["O1", "O2"]


@pytest.mark.anyio
async def test_fetch_orders_defaults_created_after_to_24h_lookback():
    """When the caller doesn't pass created_after, the connector picks a
    default lookback (24h). We assert the resulting ISO-8601 timestamp
    is within a tight window of now-24h so a callsite that just polls
    on a cadence gets a reasonable default."""
    connector = AmazonConnector()
    body = {"payload": {"Orders": []}}

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: body,
            raise_for_status=lambda: None,
        )
        before = datetime.now(timezone.utc)
        await connector.fetch_orders(access_token="LIVE-TOKEN")
        after = datetime.now(timezone.utc)

    sent = mock_get.call_args.kwargs["params"]["CreatedAfter"]
    sent_dt = datetime.strptime(sent, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    # Expect the default to be ~now-24h. Allow a 2-second tolerance on
    # each side for clock skew between the captured `before`/`after` and
    # the connector's own `datetime.now()` call.
    assert (before - sent_dt).total_seconds() >= 24 * 3600 - 2
    assert (after - sent_dt).total_seconds() <= 24 * 3600 + 2


@pytest.mark.anyio
async def test_fetch_orders_returns_stub_for_stub_or_missing_token():
    """Dev convenience: None or STUB- token → one stub order, no HTTP
    calls. Mirrors fetch_all_listings."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.get") as mock_get:
        no_token = await connector.fetch_orders(access_token=None)
        stub_token = await connector.fetch_orders(access_token="STUB-AMAZON")

    mock_get.assert_not_called()
    for orders in (no_token, stub_token):
        assert len(orders) == 1
        assert orders[0]["AmazonOrderId"] == "AMZ-STUB-ORDER-001"
        assert orders[0]["MarketplaceId"] == MEXICO_MARKETPLACE_ID


@pytest.mark.anyio
async def test_fetch_orders_handles_empty_page_safely():
    """Empty Orders list + missing NextToken → return []."""
    connector = AmazonConnector()
    body = {"payload": {"Orders": [], "NextToken": None}}

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: body,
            raise_for_status=lambda: None,
        )
        orders = await connector.fetch_orders(
            access_token="LIVE-TOKEN",
            created_after=datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc),
        )

    assert orders == []
    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# fetch_order_items
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_fetch_order_items_calls_per_order_endpoint():
    """Happy path: single SP-API page with two line items. Verifies the
    URL template (/orders/v0/orders/{id}/orderItems), header carrier,
    and raw-dict passthrough of the OrderItems list."""
    connector = AmazonConnector()
    body = {
        "payload": {
            "OrderItems": [
                {
                    "ASIN": "B000111111",
                    "SellerSKU": "SKU-A",
                    "OrderItemId": "OI-A",
                    "Title": "Item Alpha",
                    "QuantityOrdered": 2,
                    "ItemPrice": {"CurrencyCode": "MXN", "Amount": "199.00"},
                },
                {
                    "ASIN": "B000222222",
                    "SellerSKU": "SKU-B",
                    "OrderItemId": "OI-B",
                    "QuantityOrdered": 1,
                    "ItemPrice": {"CurrencyCode": "MXN", "Amount": "49.50"},
                },
            ],
        }
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: body,
            raise_for_status=lambda: None,
        )
        items = await connector.fetch_order_items(
            order_id="111-2222222-3333333",
            access_token="LIVE-TOKEN",
        )

    assert mock_get.call_count == 1
    args, kwargs = mock_get.call_args
    assert args[0].endswith("/orders/v0/orders/111-2222222-3333333/orderItems")
    assert kwargs["headers"]["x-amz-access-token"] == "LIVE-TOKEN"
    # First page → no NextToken in params
    assert "NextToken" not in kwargs["params"]

    assert [item["ASIN"] for item in items] == ["B000111111", "B000222222"]
    assert items[0]["ItemPrice"]["Amount"] == "199.00"


@pytest.mark.anyio
async def test_fetch_order_items_paginates_via_next_token():
    """Two-page response paginates via NextToken. Asserts the second
    call carries NextToken and that items concatenate across pages."""
    connector = AmazonConnector()
    page1 = {
        "payload": {
            "OrderItems": [{"OrderItemId": "OI-1", "ASIN": "A1"}],
            "NextToken": "PAGE-2",
        }
    }
    page2 = {
        "payload": {"OrderItems": [{"OrderItemId": "OI-2", "ASIN": "A2"}]}
    }
    responses = iter([page1, page2])

    def _make_response(*args, **kwargs):
        b = next(responses)
        return AsyncMock(status_code=200, json=lambda body=b: body, raise_for_status=lambda: None)

    with patch("httpx.AsyncClient.get", side_effect=_make_response) as mock_get:
        items = await connector.fetch_order_items(
            order_id="123-4567890-1234567",
            access_token="LIVE-TOKEN",
        )

    assert mock_get.call_count == 2
    assert "NextToken" not in mock_get.call_args_list[0].kwargs["params"]
    assert mock_get.call_args_list[1].kwargs["params"]["NextToken"] == "PAGE-2"
    assert [it["OrderItemId"] for it in items] == ["OI-1", "OI-2"]


@pytest.mark.anyio
async def test_fetch_order_items_returns_stub_for_stub_or_missing_token():
    """Dev convenience: None / STUB- token → one stub item, no HTTP."""
    connector = AmazonConnector()

    with patch("httpx.AsyncClient.get") as mock_get:
        none_items = await connector.fetch_order_items("AMZ-1", access_token=None)
        stub_items = await connector.fetch_order_items("AMZ-1", access_token="STUB-AMAZON")

    mock_get.assert_not_called()
    for items in (none_items, stub_items):
        assert len(items) == 1
        assert items[0]["OrderItemId"] == "STUB-ITEM-1"
        assert items[0]["SellerSKU"] == "STUB-SKU-001"
