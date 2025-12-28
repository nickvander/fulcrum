from typing import Dict, Any, Optional
import httpx
from src.config import settings
from .base import BaseMarketplaceConnector

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
        # TODO: Implement real API call: GET /users/me/items/search
        from .base import ListingData
        return [
            ListingData(
                external_id="MLM-STUB-001",
                sku="STUB-SKU-001",
                title="Stub ML Mexico Product 1",
                price=1500.0,
                status="active"
            )
        ]

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

    async def get_listing_status(self, external_id: str, access_token: Optional[str] = None) -> str:
        """
        Fetches listing status via GET /items/{item_id}.
        """
        return "active"
