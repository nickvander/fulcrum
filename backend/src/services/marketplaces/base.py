from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ListingData(BaseModel):
    """
    Standardized listing data from any marketplace.
    """
    external_id: str
    sku: Optional[str] = None
    title: str
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    currency: str = "USD"
    listing_url: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: List[str] = []
    status: str = "ACTIVE"
    available_quantity: Optional[int] = None
    raw_data: Dict[str, Any] = {}

class BaseMarketplaceConnector(ABC):
    """
    Abstract Base Class for all marketplace integrations (Amazon, MercadoLibre, etc.)
    """

    @abstractmethod
    async def get_auth_url(self) -> str:
        """Returns the URL for the user to authorize the app."""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges the authorization code for access/refresh tokens."""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token."""
        pass

    @abstractmethod
    async def fetch_all_listings(self) -> List[ListingData]:
        """Fetches all existing listings from the marketplace."""
        pass

    @abstractmethod
    async def sync_inventory(self, external_id: str, quantity: int, access_token: Optional[str] = None) -> bool:
        """Synchronizes inventory quantity to the marketplace."""
        pass

    @abstractmethod
    async def sync_price(self, external_id: str, price: float, access_token: Optional[str] = None) -> bool:
        """Synchronizes price to the marketplace."""
        pass

    @abstractmethod
    async def publish_listing(self, product_data: Dict[str, Any], access_token: Optional[str] = None) -> str:
        """Creates a new listing on the marketplace and returns the external ID."""
        pass

    @abstractmethod
    async def get_listing_status(self, external_id: str, access_token: Optional[str] = None) -> str:
        """Fetches the current status of a listing from the marketplace."""
        pass
