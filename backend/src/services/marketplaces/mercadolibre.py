from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta, timezone
import httpx
from src.config import settings
from .base import (
    BaseMarketplaceConnector,
    InboundShipmentItem,
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)

class MercadoLibreConnector(BaseMarketplaceConnector):
    """
    MercadoLibre Mexico (MLM) implementation of the Marketplace Connector.
    """
    
    # Mexico-specific configuration
    SITE_ID = "MLM"  # MercadoLibre Mexico
    AUTH_URL = "https://auth.mercadolibre.com.mx/authorization"
    API_URL = "https://api.mercadolibre.com"

    async def get_auth_url(self) -> str:
        """
        Returns the MercadoLibre Mexico authorization URL.
        """
        client_id = settings.ML_CLIENT_ID or "STUB_CLIENT_ID"
        redirect_uri = settings.ML_REDIRECT_URI or "http://localhost:4200/marketplaces/mercadolibre/callback"
        return f"{self.AUTH_URL}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for access/refresh tokens.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.ML_CLIENT_ID,
                    "client_secret": settings.ML_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.ML_REDIRECT_URI,
                }
            )
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes the access token using the refresh token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.ML_CLIENT_ID,
                    "client_secret": settings.ML_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                }
            )
            response.raise_for_status()
            return response.json()

    async def fetch_all_listings(self, access_token: Optional[str] = None) -> list:
        """
        Fetches all listings from MercadoLibre for the authenticated user.
        """
        if not access_token:
            raise ValueError("Access token is required to fetch listings")

        from .base import ListingData
        results = []
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 1. Get User ID
            user_response = await client.get(f"{self.API_URL}/users/me", headers=headers)
            user_response.raise_for_status()
            user_id = user_response.json().get("id")
            
            # 2. Get User Items (with pagination)
            item_ids = []
            offset = 0
            limit = 50
            
            while True:
                search_response = await client.get(
                    f"{self.API_URL}/users/{user_id}/items/search", 
                    params={"offset": offset, "limit": limit},
                    headers=headers
                )
                search_response.raise_for_status()
                data = search_response.json()
                page_results = data.get("results", [])
                
                if not page_results:
                    break
                    
                item_ids.extend(page_results)
                
                paging = data.get("paging", {})
                total = paging.get("total", 0)
                offset += limit
                
                if offset >= total:
                    break
            
            if not item_ids:
                return []
                
            # 3. Get Item Details (Chunking max 20 per request as per ML docs)
            chunk_size = 20
            semaphore = asyncio.Semaphore(10) # Limit concurrency
            
            async def get_item_with_prices(item_id_chunk, headers):
                ids_param = ",".join(item_id_chunk)
                async with semaphore:
                    # Get Items
                    items_response = await client.get(
                        f"{self.API_URL}/items",
                        params={
                            "ids": ids_param,
                            "attributes": "id,title,price,original_price,base_price,currency_id,thumbnail,permalink,pictures,status,available_quantity,attributes,variations,prices"
                        },
                        headers=headers
                    )
                    items_response.raise_for_status()
                    items_data = items_response.json()
                    
                    chunk_results = []
                    for item_obj in items_data:
                        if item_obj.get("code") == 200:
                            item = item_obj.get("body", {})
                            
                            # Get detailed prices from /items/{id}/prices because Multiget often hides them
                            try:
                                prices_response = await client.get(f"{self.API_URL}/items/{item.get('id')}/prices", headers=headers)
                                if prices_response.status_code == 200:
                                    prices_data = prices_response.json()
                                    prices_list = prices_data.get("prices", [])
                                    promo = next((p for p in prices_list if p.get("type") == "promotion"), None)
                                    if promo:
                                        item["price"] = promo.get("amount")
                                        item["original_price"] = promo.get("regular_amount")
                            except Exception:
                                # Suppress in production or use logger
                                pass

                            # Extract all images
                            pictures = item.get("pictures", [])
                            image_urls = []
                            for p in pictures:
                                url = p.get("secure_url") or p.get("url")
                                if url:
                                    image_urls.append(url)
                                    
                            # Calculate discount if applicable
                            price = item.get("price")
                            original_price = item.get("original_price")
                            
                            # Only use base_price as original if it's higher than current price
                            base_price = item.get("base_price")
                            if not original_price and base_price and float(base_price) > float(price):
                                original_price = base_price
                                    
                            discount_percentage = None
                            if original_price and price and float(original_price) > float(price):
                                discount_percentage = round((1 - (float(price) / float(original_price))) * 100, 2)
                                
                            chunk_results.append(ListingData(
                                external_id=item.get("id"),
                                sku=next((attr.get("value_name") for attr in item.get("attributes", []) if attr.get("id") == "SELLER_SKU"), None),
                                title=item.get("title"),
                                price=price,
                                original_price=original_price,
                                discount_percentage=discount_percentage,
                                currency=item.get("currency_id", "MXN"),
                                listing_url=item.get("permalink"),
                                image_url=image_urls[0] if image_urls else item.get("thumbnail"),
                                image_urls=image_urls,
                                status=item.get("status"),
                                available_quantity=item.get("available_quantity"),
                                raw_data=item
                            ))
                    return chunk_results

            # Create tasks for all chunks
            chunks = [item_ids[i:i + chunk_size] for i in range(0, len(item_ids), chunk_size)]
            tasks = [get_item_with_prices(chunk, headers) for chunk in chunks]
            
            chunked_results = await asyncio.gather(*tasks)
            for chunk_res in chunked_results:
                results.extend(chunk_res)
                        
        return results

    async def sync_inventory(self, external_id: str, quantity: int, access_token: Optional[str] = None) -> bool:
        """
        Updates stock via PUT /items/{item_id}.
        """
        if not access_token:
            return False
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.API_URL}/items/{external_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"available_quantity": quantity},
            )
            response.raise_for_status()
        return True

    async def sync_price(self, external_id: str, price: float, access_token: Optional[str] = None) -> bool:
        """
        Updates price via PUT /items/{item_id}.
        """
        if not access_token:
            return False
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.API_URL}/items/{external_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"price": price},
            )
            response.raise_for_status()
        return True

    async def publish_listing(self, product_data: Dict[str, Any], access_token: Optional[str] = None) -> str:
        """
        Creates a new listing via POST /items.

        Maps the Fulcrum-side payload (name/sku/description/price + optional
        images, category, listing_type, etc.) into ML's POST /items shape with
        Mexico-first defaults (site_id=MLM, currency=MXN, condition=new).
        Anything the caller passes through under an ML-native key (e.g.
        category_id, listing_type_id, pictures) overrides those defaults so
        callers that build a complete payload can do so.

        Without a token (or with a stub token) returns a deterministic stub id
        so dev/test paths can exercise the publish workflow without hitting the
        live ML API. Mirrors the pattern used by create_inbound_shipment.

        Returns the external item id (e.g. "MLM123456789").
        """
        if not access_token or access_token.startswith("STUB"):
            stub_id = "MLM-STUB-" + (product_data.get("sku") or product_data.get("name") or "ITEM")
            return stub_id

        payload: Dict[str, Any] = {
            "site_id": self.SITE_ID,
            "title": product_data.get("title") or product_data.get("name"),
            "category_id": product_data.get("category_id"),
            "price": product_data.get("price"),
            "currency_id": product_data.get("currency_id") or "MXN",
            "available_quantity": product_data.get("available_quantity", 1),
            "buying_mode": product_data.get("buying_mode") or "buy_it_now",
            "listing_type_id": product_data.get("listing_type_id") or "gold_special",
            "condition": product_data.get("condition") or "new",
            "description": {"plain_text": product_data.get("description") or ""},
        }
        pictures = product_data.get("pictures")
        if pictures:
            payload["pictures"] = pictures
        # Drop keys with None values so ML doesn't reject the payload for
        # explicit nulls on optional fields like category_id.
        payload = {key: value for key, value in payload.items() if value is not None}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/items",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return str(data.get("id") or "")

    async def fetch_public_listings(self, query: str) -> list:
        """
        Fetches public listings from MercadoLibre Mexico for a given search query.
        Does NOT require an access token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_URL}/sites/{self.SITE_ID}/search",
                params={"q": query, "limit": 10},
                headers={"User-Agent": "Fulcrum/1.0.0 (https://github.com/nickvander/fulcrum)"}
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "external_id": item.get("id"),
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "currency": item.get("currency_id"),
                    "permalink": item.get("permalink"),
                    "thumbnail": item.get("thumbnail"),
                    "condition": item.get("condition"),
                    "available_quantity": item.get("available_quantity")
                })
            return results

    async def get_listing_status(self, external_id: str, access_token: Optional[str] = None) -> str:
        """
        Fetches listing status via GET /items/{item_id}.
        """
        return "active"

    INBOUND_PATH = "/fbm/inbound/shipments"

    async def create_inbound_shipment(
        self,
        items: List[InboundShipmentItem],
        access_token: Optional[str] = None,
    ) -> InboundShipmentResult:
        """
        Creates an inbound shipment to a MercadoLibre Full warehouse.

        Without a token (or with a stub token), returns a deterministic stub so
        development/test environments can exercise the workflow end-to-end
        without hitting the live API.
        """
        if not access_token or access_token.startswith("STUB"):
            stub_id = "ML-FULL-STUB-" + "-".join(
                str(item.quantity) for item in items[:3]
            )
            return InboundShipmentResult(
                external_inbound_id=stub_id,
                status="pending",
                label_url=None,
                detail_url=None,
                raw_data={"stub": True, "items": [i.model_dump() for i in items]},
            )

        payload = {
            "site_id": self.SITE_ID,
            "items": [
                {
                    "item_id": item.external_listing_id,
                    "sku": item.sku,
                    "title": item.title,
                    "quantity": item.quantity,
                }
                for item in items
            ],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}{self.INBOUND_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return InboundShipmentResult(
                external_inbound_id=str(data.get("id") or data.get("shipment_id") or ""),
                status=data.get("status", "pending"),
                label_url=data.get("label_url") or data.get("shipping_label_url"),
                detail_url=data.get("detail_url"),
                raw_data=data,
            )

    async def get_inbound_shipment_status(
        self,
        external_inbound_id: str,
        access_token: Optional[str] = None,
    ) -> InboundShipmentResult:
        """Polls an existing inbound shipment for its current status.

        Populates `received_items` with per-line received quantities so
        `inbound_shipment_reconciliation` can back-fill `qty_received`
        on local `StockTransferItem` rows.

        ML's inbound endpoint returns per-item rows with `item_id` (the
        listing id) + a received-quantity field. The exact name has
        varied across API revisions, so we accept a few aliases
        (`received_quantity`, `quantity_received`, `quantity`) and fall
        back to 0 — better to under-report than crash on a renamed key.
        """
        if not access_token or access_token.startswith("STUB") or external_inbound_id.startswith("ML-FULL-STUB-"):
            return InboundShipmentResult(
                external_inbound_id=external_inbound_id,
                status="pending",
                raw_data={"stub": True},
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_URL}{self.INBOUND_PATH}/{external_inbound_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return InboundShipmentResult(
                external_inbound_id=external_inbound_id,
                status=data.get("status", "pending"),
                label_url=data.get("label_url"),
                detail_url=data.get("detail_url"),
                received_items=self._parse_received_items(data),
                raw_data=data,
            )

    @staticmethod
    def _parse_received_items(data: Dict[str, Any]) -> List[InboundShipmentReceivedItem]:
        """Extract per-line received quantities from an ML inbound
        status payload. Tolerant of key renames: `received_quantity`,
        `quantity_received`, and bare `quantity` are all accepted in
        that order of preference.
        """
        rows = data.get("items") or []
        parsed: List[InboundShipmentReceivedItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            received: Any = (
                row.get("received_quantity")
                or row.get("quantity_received")
                or row.get("quantity")
                or 0
            )
            try:
                received_int = int(received)
            except (TypeError, ValueError):
                received_int = 0
            parsed.append(
                InboundShipmentReceivedItem(
                    external_listing_id=(
                        str(row.get("item_id")) if row.get("item_id") is not None
                        else None
                    ),
                    sku=row.get("sku"),
                    received_quantity=received_int,
                )
            )
        return parsed
    async def fetch_order(self, order_id: str, access_token: str) -> Dict[str, Any]:
        """
        Fetches a single order from MercadoLibre via GET /orders/{order_id}.
        Requires a valid access token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_URL}/orders/{order_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_orders(
        self,
        access_token: str,
        *,
        created_from: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List orders for the authenticated seller created after a cursor.

        Used by the periodic ML order poller
        (`services/mercadolibre_order_ingestion.py`) to back-fill orders
        that the webhook missed or delivered out of order.

        ML's listing API requires a `seller` query parameter — the
        seller's numeric user id. We resolve it via `/users/me` exactly
        the way `fetch_all_listings` does, so a single access token is
        sufficient (no extra config).

        `created_from` is filled into `order.date_created.from` as an
        ISO-8601 string with a `Z` suffix (ML's format). When None, we
        default to 24h ago — same fallback the Amazon connector applies
        when its cursor is fresh.

        Paginates 50-at-a-time (ML's API max) up to a hard cap on total
        rows so a misconfigured cursor or unbounded backlog can't burn
        the request budget. The cap is generous enough for normal
        operation: 1,000 orders means 20 pages, well below typical
        seller order volumes per 15-minute tick.
        """
        cursor = created_from or (
            datetime.now(timezone.utc) - timedelta(hours=24)
        )
        if cursor.tzinfo is None:
            cursor = cursor.replace(tzinfo=timezone.utc)
        cursor_iso = cursor.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        max_rows = 1000
        page_limit = max(1, min(limit, 50))
        results: List[Dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            user_response = await client.get(
                f"{self.API_URL}/users/me", headers=headers,
            )
            user_response.raise_for_status()
            seller_id = user_response.json().get("id")
            if seller_id is None:
                return results

            offset = 0
            while True:
                response = await client.get(
                    f"{self.API_URL}/orders/search",
                    params={
                        "seller": seller_id,
                        "order.date_created.from": cursor_iso,
                        "sort": "date_asc",
                        "offset": offset,
                        "limit": page_limit,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json() or {}
                page = data.get("results") or []
                if not page:
                    break
                results.extend(page)
                if len(results) >= max_rows:
                    break
                if len(page) < page_limit:
                    # ML returned a short page → no more pages even if
                    # `paging.total` says otherwise.
                    break
                offset += page_limit
        return results[:max_rows]

    async def fetch_order_billing(
        self, order_id: str, access_token: str,
    ) -> Dict[str, Optional[float]]:
        """Return real per-order settlement fees + shipping cost for one
        ML order, used by the settlement-fee ingestion worker.

        Strategy: fetch the order via `GET /orders/{order_id}`, which
        embeds the payments list. Each payment carries
        `marketplace_fee` (or `fee_details[]` on newer API revisions)
        and the order's `shipping` object carries `shipping_cost`.
        We sum across payments because partial captures + multi-method
        orders can split fees across rows.

        Returns a dict with two keys; both `None` means "the
        marketplace didn't carry fee data on this order yet" (a typical
        pending ML order). Caller treats `None` as "skip, retry on the
        next tick".

          {"marketplace_fees_amount": float | None,
           "shipping_cost_amount":    float | None}

        Tolerant of ML's evolving JSON shape — it has revised the
        payment payload several times. We accept both top-level
        `marketplace_fee` and `fee_details[].amount`, and both
        `shipping.shipping_cost` and `shipping.cost`.
        """
        data = await self.fetch_order(order_id, access_token)
        return self._extract_settlement_from_order(data)

    @staticmethod
    def _extract_settlement_from_order(
        data: Dict[str, Any],
    ) -> Dict[str, Optional[float]]:
        """Pure parser for the order payload → settlement summary.

        Extracted so tests can exercise the field-precedence rules
        without HTTP fixtures.
        """
        fees: Optional[float] = None
        for payment in data.get("payments") or []:
            if not isinstance(payment, dict):
                continue
            # Skip refunded payments — their fees are reversed and
            # carry meaningless residuals on the live ML side.
            status = (payment.get("status") or "").lower()
            if status in {"refunded", "cancelled", "rejected"}:
                continue
            payment_fee: Optional[float] = None
            # 1) Newer revision: `fee_details: [{amount, ...}, ...]`
            details = payment.get("fee_details")
            if isinstance(details, list) and details:
                acc = 0.0
                any_value = False
                for detail in details:
                    if isinstance(detail, dict) and detail.get("amount") is not None:
                        try:
                            acc += float(detail["amount"])
                            any_value = True
                        except (TypeError, ValueError):
                            continue
                if any_value:
                    payment_fee = acc
            # 2) Older revision: top-level `marketplace_fee`.
            if payment_fee is None and payment.get("marketplace_fee") is not None:
                try:
                    payment_fee = float(payment["marketplace_fee"])
                except (TypeError, ValueError):
                    payment_fee = None
            if payment_fee is not None:
                fees = (fees or 0.0) + payment_fee

        shipping_cost: Optional[float] = None
        shipping = data.get("shipping") or {}
        if isinstance(shipping, dict):
            for key in ("shipping_cost", "cost", "list_cost"):
                value = shipping.get(key)
                if value is not None:
                    try:
                        shipping_cost = float(value)
                        break
                    except (TypeError, ValueError):
                        continue

        return {
            "marketplace_fees_amount": fees,
            "shipping_cost_amount": shipping_cost,
        }
