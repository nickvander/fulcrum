from abc import ABC, abstractmethod
from typing import Dict, Any

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
    async def sync_inventory(self, external_id: str, quantity: int) -> bool:
        """Synchronizes inventory quantity to the marketplace."""
        pass

    @abstractmethod
    async def sync_price(self, external_id: str, price: float) -> bool:
        """Synchronizes price to the marketplace."""
        pass

    @abstractmethod
    async def publish_listing(self, product_data: Dict[str, Any]) -> str:
        """Creates a new listing on the marketplace and returns the external ID."""
        pass

    @abstractmethod
    async def get_listing_status(self, external_id: str) -> str:
        """Fetches the current status of a listing from the marketplace."""
        pass
