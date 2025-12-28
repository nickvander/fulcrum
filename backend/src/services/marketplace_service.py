from typing import Dict, Any, Type
from sqlalchemy.orm import Session
from src.services.marketplaces.base import BaseMarketplaceConnector
from src.services.marketplaces.mercadolibre import MercadoLibreConnector
from src.services.marketplaces.amazon import AmazonConnector

class MarketplaceService:
    """
    Orchestrator service that manages marketplace connections and operations.
    Uses the Strategy pattern to delegate to specific connectors.
    """

    def __init__(self):
        self._connectors: Dict[str, Type[BaseMarketplaceConnector]] = {
            "mercadolibre": MercadoLibreConnector,
            "amazon": AmazonConnector
        }
        self._instances: Dict[str, BaseMarketplaceConnector] = {}

    def get_connector(self, marketplace_name: str) -> BaseMarketplaceConnector:
        """
        Factory method to get the correct connector instance for a marketplace.
        """
        name = marketplace_name.lower()
        if name not in self._connectors:
            raise ValueError(f"Unsupported marketplace: {marketplace_name}")
        
        if name not in self._instances:
            self._instances[name] = self._connectors[name]()
        
        return self._instances[name]

    async def sync_product_inventory(self, db: Session, marketplace_name: str, external_id: str, quantity: int) -> bool:
        """
        Syncs inventory for a specific product listing on a marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.sync_inventory(external_id, quantity)

    async def publish_listing(self, db: Session, marketplace_name: str, product_data: Dict[str, Any]) -> str:
        """
        Publishes a product to the specified marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.publish_listing(product_data)

# Singleton instance
marketplace_service = MarketplaceService()
