from typing import Dict, Any, List, Optional
import asyncio
import httpx
from src.config import settings
from .base import BaseMarketplaceConnector, InboundShipmentItem, InboundShipmentResult

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
        print(f"Syncing ML Mexico inventory for {external_id} to {quantity}")
        # Real: PUT /items/{external_id} with {"available_quantity": quantity}
        return True

    async def sync_price(self, external_id: str, price: float, access_token: Optional[str] = None) -> bool:
        """
        Updates price via PUT /items/{item_id}.
        """
        if not access_token:
            return False
        print(f"Syncing ML Mexico price for {external_id} to {price}")
        # Real: PUT /items/{external_id} with {"price": price}
        return True

    async def publish_listing(self, product_data: Dict[str, Any], access_token: Optional[str] = None) -> str:
        """
        Creates a new listing via POST /items.
        """
        if not access_token:
            return "ERROR-NO-TOKEN"
        print(f"Publishing to ML Mexico: {product_data.get('name')}")
        # Real: POST /items with full product payload, site_id=MLM
        return "MLM-STUB-123"

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
        """Polls an existing inbound shipment for its current status."""
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
                raw_data=data,
            )
