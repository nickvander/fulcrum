from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import httpx
from src.config import settings
from .base import (
    BaseMarketplaceConnector,
    InboundShipmentReceivedItem,
    InboundShipmentResult,
    ListingData,
)

# Mexico is Fulcrum's primary Amazon market. The SP-API requires at least
# one marketplaceId on listings reads and most attribute writes.
MEXICO_MARKETPLACE_ID = "A1AM78C64UM0Y8"

# Default lookback for fetch_orders when the caller doesn't pass
# created_after. Matches the cadence of how Fulcrum polls today (hourly /
# on-demand) — anything older than this should be reconciled via webhooks
# or a longer backfill, not the default poll path.
_DEFAULT_ORDER_LOOKBACK = timedelta(days=1)


class AmazonConnector(BaseMarketplaceConnector):
    """
    Amazon SP-API implementation of the Marketplace Connector.
    """


    @property
    def api_base_url(self) -> str:
        if settings.AMAZON_SANDBOX:
            return "https://sandbox.sellingpartnerapi-na.amazon.com"
        return "https://sellingpartnerapi-na.amazon.com"

    async def get_auth_url(self) -> str:
        """
        Returns the Amazon Seller Central authorization URL.
        """
        app_id = settings.AMAZON_CLIENT_ID or "STUB_APP_ID"
        # version=beta allows testing before the app is published in the marketplace
        return f"https://sellercentral.amazon.com/apps/authorize/consent?application_id={app_id}&version=beta"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for LWA tokens.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.AMAZON_CLIENT_ID,
                    "client_secret": settings.AMAZON_CLIENT_SECRET,
                }
            )
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes the LWA access token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.AMAZON_CLIENT_ID,
                    "client_secret": settings.AMAZON_CLIENT_SECRET,
                }
            )
            response.raise_for_status()
            return response.json()

    async def fetch_all_listings(self, access_token: Optional[str] = None) -> List[ListingData]:
        """
        Page through the seller's Amazon Mexico catalog via the SP-API
        Listings API and return one ListingData per item.

        Endpoint: GET /listings/2021-08-01/items/{sellerId}
            - marketplaceIds=A1AM78C64UM0Y8 (Mexico)
            - includedData=summaries,offers so we get itemName / asin /
              status / price in a single round trip
            - pageToken/nextToken for pagination — Amazon defaults to
              10 items per page and there is no upper-bound override

        Returns a stub list when there's no access_token, or when the
        token starts with "STUB-" (dev/test convenience matching the
        publish_listing pattern). Without this, every local test run
        and every dev workspace would need a live SP-API token just to
        render the Marketplaces page.
        """
        if not access_token or access_token.startswith("STUB-"):
            return [
                ListingData(
                    external_id="AMZ-STUB-ASIN-001",
                    sku="STUB-SKU-001",
                    title="Stub Amazon Product 1",
                    price=19.99,
                    status="BUYABLE",
                ),
            ]

        seller_id = settings.AMAZON_SELLER_ID
        url = f"{self.api_base_url}/listings/2021-08-01/items/{seller_id}"
        headers = {"x-amz-access-token": access_token}
        results: List[ListingData] = []
        page_token: Optional[str] = None

        async with httpx.AsyncClient() as client:
            while True:
                params: Dict[str, Any] = {
                    "marketplaceIds": MEXICO_MARKETPLACE_ID,
                    "includedData": "summaries,offers",
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                body = response.json()

                for item in body.get("items", []) or []:
                    results.append(self._parse_listing_item(item))

                # SP-API's pagination key on this endpoint is nextToken
                # nested under "pagination". Empty / missing → stop.
                page_token = (body.get("pagination") or {}).get("nextToken")
                if not page_token:
                    break

        return results

    @staticmethod
    def _parse_listing_item(item: Dict[str, Any]) -> ListingData:
        """Map one SP-API Listings item into the canonical ListingData
        shape. Defensive about missing nested fields — SP-API responses
        regularly omit optional sections, and a partial mapping is
        better than dropping the listing."""
        summaries = item.get("summaries") or []
        primary = next(
            (s for s in summaries if s.get("marketplaceId") == MEXICO_MARKETPLACE_ID),
            summaries[0] if summaries else {},
        )

        offers = item.get("offers") or []
        price_obj = (offers[0].get("price") if offers else None) or {}
        amount = price_obj.get("amount")
        try:
            price = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            price = None

        status_list = primary.get("status") or []
        status = status_list[0] if status_list else "ACTIVE"

        return ListingData(
            external_id=primary.get("asin") or item.get("sku", ""),
            sku=item.get("sku"),
            title=primary.get("itemName") or "",
            price=price,
            currency=price_obj.get("currencyCode") or "MXN",
            status=status,
            raw_data=item,
        )

    async def sync_inventory(self, external_id: str, quantity: int, access_token: Optional[str] = None) -> bool:
        """
        PATCH the seller's merchant-fulfilled stock for a single SKU on
        Amazon Mexico via the Listings Items API.

        Endpoint: PATCH /listings/2021-08-01/items/{sellerId}/{sku}
            - marketplaceIds=A1AM78C64UM0Y8 query param is REQUIRED by
              SP-API; without it the request 400s.
            - patches=[{op:replace, path:/attributes/fulfillment_availability,
              value:[{fulfillment_channel_code:DEFAULT, quantity:N}]}]
              DEFAULT == merchant-fulfilled (MFN); AMAZON_NA would be FBA.

        Returns True on a 2xx response. Lets `httpx.HTTPStatusError`
        propagate so that MarketplaceService.call_with_401_retry can
        force-refresh the token and retry on a stale-token 401 — the old
        bare-except swallowed every error including 401 and broke that
        flow.

        Stub-token branch (None or "STUB-…") returns True without
        hitting the network, mirroring fetch_all_listings/publish_listing.
        """
        if not access_token or access_token.startswith("STUB-"):
            return True

        seller_id = settings.AMAZON_SELLER_ID
        url = f"{self.api_base_url}/listings/2021-08-01/items/{seller_id}/{external_id}"
        params = {"marketplaceIds": MEXICO_MARKETPLACE_ID}
        payload = {
            "productType": "PRODUCT",
            "patches": [
                {
                    "op": "replace",
                    "path": "/attributes/fulfillment_availability",
                    "value": [
                        {
                            "fulfillment_channel_code": "DEFAULT",
                            "quantity": quantity,
                        }
                    ],
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                params=params,
                json=payload,
                headers={"x-amz-access-token": access_token},
            )
            response.raise_for_status()
        return True

    async def sync_price(self, external_id: str, price: float, access_token: Optional[str] = None) -> bool:
        if not access_token:
            return False
            
        print(f"Syncing Amazon price for {external_id} to {price}")
        return True # Similar implementation to inventory

    async def publish_listing(self, product_data: Dict[str, Any], access_token: Optional[str] = None) -> str:
        if not access_token:
            return "ERROR-NO-TOKEN"
            
        sku = product_data.get('sku')
        print(f"Publishing to Amazon: {product_data.get('name')} (SKU: {sku})")
        
        seller_id = settings.AMAZON_SELLER_ID
        url = f"{self.api_base_url}/listings/2021-08-01/items/{seller_id}/{sku}"
        
        # PUT payload
        payload = {
            "productType": "PRODUCT",
            "attributes": {
                "item_name": [{"value": product_data.get("name"), "language_tag": "en_US"}],
                "purchasable_offer": [{"currency": "USD", "our_price": [{"amount": product_data.get("price")}]}]
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(url, json=payload, headers={"x-amz-access-token": access_token})
                print(f"Amazon Publish Response: {response.status_code}")
                # Sandbox returns 200/202
                return sku # Use SKU as external ID for Amazon
            except Exception as e:
                print(f"Amazon Publish Error: {e}")
                return "ERROR-PUBLISH"

    async def get_listing_status(self, external_id: str, access_token: Optional[str] = None) -> str:
        return "BUYABLE"

    async def fetch_orders(
        self,
        access_token: Optional[str] = None,
        created_after: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Page through the seller's recent Amazon Mexico orders via the
        SP-API Orders v0 API.

        Endpoint: GET /orders/v0/orders
            - MarketplaceIds=A1AM78C64UM0Y8 (Mexico) — required.
            - CreatedAfter=<ISO-8601 UTC> — required when NextToken is
              absent. Defaults to now-24h if the caller doesn't pass one.
            - NextToken from the previous page's payload.NextToken. When
              paginating, SP-API rejects requests that re-pass
              MarketplaceIds/CreatedAfter alongside NextToken, so the
              second-page request carries only NextToken + MarketplaceIds.

        Returns the raw SP-API order dicts (one per AmazonOrderId) —
        mirrors `MercadoLibreConnector.fetch_order`, which also returns
        the marketplace's raw payload. Adding an `OrderData` canonical
        shape is deferred until there's a second consumer beyond the
        eventual order-sync worker.

        Stub-token branch (None or "STUB-…") returns a single stub order
        without hitting the network, same convention as
        fetch_all_listings.
        """
        if not access_token or access_token.startswith("STUB-"):
            return [
                {
                    "AmazonOrderId": "AMZ-STUB-ORDER-001",
                    "PurchaseDate": "2026-05-17T00:00:00Z",
                    "OrderStatus": "Shipped",
                    "OrderTotal": {"CurrencyCode": "MXN", "Amount": "199.00"},
                    "MarketplaceId": MEXICO_MARKETPLACE_ID,
                }
            ]

        if created_after is None:
            created_after = datetime.now(timezone.utc) - _DEFAULT_ORDER_LOOKBACK
        # SP-API wants ISO-8601 UTC; trim microseconds for stability and
        # use the "Z" suffix the docs use in their examples.
        created_after_iso = (
            created_after.astimezone(timezone.utc)
            .replace(microsecond=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        url = f"{self.api_base_url}/orders/v0/orders"
        headers = {"x-amz-access-token": access_token}
        results: List[Dict[str, Any]] = []
        next_token: Optional[str] = None

        async with httpx.AsyncClient() as client:
            while True:
                if next_token:
                    params: Dict[str, Any] = {
                        "MarketplaceIds": MEXICO_MARKETPLACE_ID,
                        "NextToken": next_token,
                    }
                else:
                    params = {
                        "MarketplaceIds": MEXICO_MARKETPLACE_ID,
                        "CreatedAfter": created_after_iso,
                    }

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = (response.json() or {}).get("payload") or {}

                for order in payload.get("Orders") or []:
                    results.append(order)

                next_token = payload.get("NextToken")
                if not next_token:
                    break

        return results

    async def fetch_order_items(
        self,
        order_id: str,
        access_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch the line items for one Amazon order.

        Endpoint: GET /orders/v0/orders/{AmazonOrderId}/orderItems
            - NextToken pagination, same shape as /orders/v0/orders.
            - No required query params beyond the path component (the
              order already carries its marketplace context).

        Returns the raw SP-API OrderItem dicts (one per line). Mirrors
        fetch_orders's raw-passthrough convention so the ingestion
        service owns the SalesOrderItem mapping.

        Stub-token branch returns one stub item — same convention as
        fetch_orders / fetch_all_listings so the order-ingestion worker
        can be exercised end-to-end without a live SP-API session.
        """
        if not access_token or access_token.startswith("STUB-"):
            return [
                {
                    "ASIN": "B000STUBITEM",
                    "SellerSKU": "STUB-SKU-001",
                    "OrderItemId": "STUB-ITEM-1",
                    "Title": "Stub Amazon Item",
                    "QuantityOrdered": 1,
                    "ItemPrice": {"CurrencyCode": "MXN", "Amount": "199.00"},
                }
            ]

        url = f"{self.api_base_url}/orders/v0/orders/{order_id}/orderItems"
        headers = {"x-amz-access-token": access_token}
        results: List[Dict[str, Any]] = []
        next_token: Optional[str] = None

        async with httpx.AsyncClient() as client:
            while True:
                params: Dict[str, Any] = {}
                if next_token:
                    params["NextToken"] = next_token

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = (response.json() or {}).get("payload") or {}

                for item in payload.get("OrderItems") or []:
                    results.append(item)

                next_token = payload.get("NextToken")
                if not next_token:
                    break

        return results

    # -- Settlement / Finances ---------------------------------------------

    # SP-API Finances v0 — per-order financial events. Returns a
    # ShipmentEventList with FeeList entries (Commission, FBAFee,
    # FBAPerOrderFulfillmentFee, ...) plus a separate ShippingChargeList
    # for the buyer-paid shipping (refunded back via shipping cost when
    # FBM). Single GET per order, paginated via NextToken if Amazon
    # decided to split the order into multiple events (rare in
    # practice).
    FINANCES_PATH = "/finances/v0/orders/{order_id}/financialEvents"

    async def fetch_order_financials(
        self,
        order_id: str,
        access_token: Optional[str] = None,
    ) -> Dict[str, Optional[float]]:
        """Return real per-order settlement fees + shipping cost for one
        Amazon order, used by the settlement-fee ingestion worker.

        Endpoint: GET /finances/v0/orders/{orderId}/financialEvents
            - Returns a FinancialEvents payload whose ShipmentEventList
              contains per-line ShipmentItemList entries; each item has
              an `ItemFeeList` of `{FeeType, FeeAmount: {Amount,
              CurrencyCode}}` rows. We sum every fee across all items
              of all shipments — Commission + FBAPerOrderFulfillmentFee
              + FBAWeightBasedFee + ... — to produce the single
              `marketplace_fees_amount` value the cost engine consumes.
            - Shipping is treated separately: the order can carry both
              charges (positive) and refunds (negative). We sum across
              both lists so a partially-refunded order shows the net.

        Returns the canonical settlement-summary dict; both values may
        be `None` when the event list is empty (Amazon hasn't settled
        the order yet — typical for pending shipments). Caller treats
        `None` as "skip, retry next tick".

        Stub-token branch returns a deterministic value so the
        worker can be exercised end-to-end without a live SP-API
        session.
        """
        if not access_token or access_token.startswith("STUB-"):
            return {
                "marketplace_fees_amount": 19.50,
                "shipping_cost_amount": 0.0,
            }

        url = f"{self.api_base_url}{self.FINANCES_PATH.format(order_id=order_id)}"
        headers = {"x-amz-access-token": access_token}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = (response.json() or {}).get("payload") or {}

        return self._extract_settlement_from_events(
            payload.get("FinancialEvents") or {},
        )

    @staticmethod
    def _extract_settlement_from_events(
        events: Dict[str, Any],
    ) -> Dict[str, Optional[float]]:
        """Pure parser for the SP-API FinancialEvents payload → settlement
        summary. Extracted so tests can run on fixture JSON without
        touching the network.

        Sum rules:
          - `marketplace_fees_amount`: sum of all `ItemFeeList[].FeeAmount.Amount`
            across all shipment items in all shipment events. Refund
            events also contribute (their fees are typically negative,
            net out to the residual).
          - `shipping_cost_amount`: sum of `ShippingChargeList[].ChargeAmount.Amount`
            across all events; refunds in the refund event list net
            against charges.

        Returns `None` for either field when no events of that type
        exist in the payload, so the caller can tell "not settled yet"
        from "actually zero".
        """
        fees_seen = False
        fees_total = 0.0
        shipping_seen = False
        shipping_total = 0.0

        def _add_amount(value: Any, acc: float, seen: bool) -> tuple[float, bool]:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return acc, seen
            return acc + num, True

        shipment_lists = (
            ("ShipmentEventList", 1.0),
            ("RefundEventList", 1.0),
            ("ChargebackEventList", 1.0),
        )
        for key, _sign in shipment_lists:
            for event in events.get(key) or []:
                if not isinstance(event, dict):
                    continue
                for item in event.get("ShipmentItemList") or []:
                    if not isinstance(item, dict):
                        continue
                    for fee in item.get("ItemFeeList") or []:
                        if not isinstance(fee, dict):
                            continue
                        amount = (fee.get("FeeAmount") or {}).get("Amount")
                        if amount is None:
                            continue
                        fees_total, fees_seen = _add_amount(amount, fees_total, fees_seen)
                for charge in event.get("ShippingChargeList") or []:
                    if not isinstance(charge, dict):
                        continue
                    amount = (charge.get("ChargeAmount") or {}).get("Amount")
                    if amount is None:
                        continue
                    shipping_total, shipping_seen = _add_amount(
                        amount, shipping_total, shipping_seen,
                    )

        return {
            "marketplace_fees_amount": (
                abs(fees_total) if fees_seen else None
            ),
            "shipping_cost_amount": (
                shipping_total if shipping_seen else None
            ),
        }

    # -- Inbound shipments (FBA) -------------------------------------------

    # Amazon's FBA Inbound v0 API is split across two endpoints — the
    # shipment-level status doc and a paginated items endpoint. We hit
    # both per poll because the shipment-status lookup doesn't include
    # per-SKU received counts, and the items endpoint doesn't include
    # the overall ShipmentStatus.
    FBA_INBOUND_PATH = "/fba/inbound/v0/shipments"

    async def get_inbound_shipment_status(
        self,
        external_inbound_id: str,
        access_token: Optional[str] = None,
    ) -> InboundShipmentResult:
        """Poll an Amazon FBA inbound shipment for its current status +
        per-item received counts.

        Two SP-API calls:
          1. GET /fba/inbound/v0/shipments/{shipmentId} →
             `ShipmentStatus` (WORKING, READY_TO_SHIP, SHIPPED,
             RECEIVING, CLOSED, CANCELLED, DELETED, ERROR, etc.). We
             surface the lowercased version on `InboundShipmentResult.status`
             for parity with ML's pending/receiving/received strings.
          2. GET /fba/inbound/v0/shipments/{shipmentId}/items → an
             array of items with `SellerSKU`, `QuantityShipped`, and
             `QuantityReceived`. Folded into `InboundShipmentReceivedItem`
             rows so the marketplace-agnostic reconciliation service
             can consume them uniformly with ML.

        Stub-token branch returns an empty `received_items` list — same
        convention as the other Amazon connector methods so the dev /
        test environments don't need a live SP-API session.
        """
        if (
            not access_token
            or access_token.startswith("STUB-")
            or not external_inbound_id
            or external_inbound_id.startswith("STUB")
        ):
            return InboundShipmentResult(
                external_inbound_id=external_inbound_id or "",
                status="pending",
                raw_data={"stub": True},
            )

        headers = {"x-amz-access-token": access_token}
        shipment_url = (
            f"{self.api_base_url}{self.FBA_INBOUND_PATH}/{external_inbound_id}"
        )
        items_url = f"{shipment_url}/items"
        params = {"MarketplaceId": MEXICO_MARKETPLACE_ID}

        async with httpx.AsyncClient() as client:
            shipment_response = await client.get(
                shipment_url, headers=headers, params=params,
            )
            shipment_response.raise_for_status()
            shipment_payload = (shipment_response.json() or {}).get("payload") or {}

            # SP-API returns the shipment object under different keys
            # depending on whether the endpoint variant uses
            # `InboundShipmentData` or `InboundShipmentInfo`. Handle
            # both so we don't crash on a minor API revision.
            shipment_obj = (
                shipment_payload.get("InboundShipmentData")
                or shipment_payload.get("InboundShipmentInfo")
                or shipment_payload
            )
            raw_status = shipment_obj.get("ShipmentStatus") or "pending"

            # Paginate the items endpoint — Amazon caps results per
            # page and returns a NextToken for the rest. Each item
            # carries its own per-SKU received count.
            received_items: List[InboundShipmentReceivedItem] = []
            next_token: Optional[str] = None
            while True:
                items_params: Dict[str, Any] = {
                    "MarketplaceId": MEXICO_MARKETPLACE_ID,
                }
                if next_token:
                    items_params["NextToken"] = next_token

                items_response = await client.get(
                    items_url, headers=headers, params=items_params,
                )
                items_response.raise_for_status()
                items_payload = (
                    (items_response.json() or {}).get("payload") or {}
                )

                for row in items_payload.get("ItemData") or []:
                    received_items.append(
                        self._parse_inbound_item(row)
                    )

                next_token = items_payload.get("NextToken")
                if not next_token:
                    break

        return InboundShipmentResult(
            external_inbound_id=external_inbound_id,
            status=str(raw_status).lower(),
            received_items=received_items,
            raw_data={
                "shipment": shipment_obj,
                "item_count": len(received_items),
            },
        )

    @staticmethod
    def _parse_inbound_item(row: Dict[str, Any]) -> InboundShipmentReceivedItem:
        """Map one SP-API FBA inbound item row to the canonical
        `InboundShipmentReceivedItem` shape.

        Amazon returns `SellerSKU` as the only consistently-present
        identifier. We populate BOTH `external_listing_id` AND `sku`
        with that value so the reconciliation service's two-step
        resolution (`MarketplaceListing.external_listing_id` first,
        `Product.sku` fallback) works regardless of whether the
        seller's `MarketplaceListing` rows are keyed by ASIN or SKU.

        Defensive about `QuantityReceived` — SP-API has occasionally
        sent it as a string. `int(...)` with a TypeError/ValueError
        fallback to 0 is safer than crashing the whole poll.
        """
        seller_sku = row.get("SellerSKU") or ""
        raw_qty = row.get("QuantityReceived") or 0
        try:
            qty = int(raw_qty)
        except (TypeError, ValueError):
            qty = 0
        return InboundShipmentReceivedItem(
            external_listing_id=str(seller_sku) if seller_sku else None,
            sku=str(seller_sku) if seller_sku else None,
            received_quantity=qty,
        )
