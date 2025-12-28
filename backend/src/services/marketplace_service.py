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

    async def sync_product_inventory(self, db: Session, marketplace_name: str, external_id: str, quantity: int, access_token: str = None) -> bool:
        """
        Syncs inventory for a specific product listing on a marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.sync_inventory(external_id, quantity, access_token=access_token)

    async def publish_listing(self, db: Session, marketplace_name: str, product_data: Dict[str, Any]) -> str:
        """
        Publishes a product to the specified marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.publish_listing(product_data)

    async def get_valid_access_token(self, db: Session, credential_id: int) -> str:
        """
        Retrieves a valid access token, refreshing it if it's expired.
        """
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
        from datetime import datetime, timedelta, timezone
        
        db_cred = crud_cred.get(db, id=credential_id)
        if not db_cred:
            raise ValueError(f"Credential with ID {credential_id} not found.")
        
        # Check if expired (with 1-minute buffer)
        is_expired = False
        if db_cred.expires_at:
            # db_cred.expires_at is timezone-aware (UTC)
            is_expired = db_cred.expires_at <= (datetime.now(timezone.utc) + timedelta(minutes=1))
        
        if not is_expired:
            return crud_cred.get_decrypted_access_token(db_cred)
        
        # Refresh needed
        refresh_token = crud_cred.get_decrypted_refresh_token(db_cred)
        if not refresh_token:
            raise ValueError("Access token expired and no refresh token available.")
        
        connector = self.get_connector(db_cred.marketplace.name)
        new_tokens = await connector.refresh_token(refresh_token)
        
        # Update credentials in DB
        from src.schemas.marketplace_credential import MarketplaceCredentialUpdate
        expires_at = None
        if "expires_in" in new_tokens:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens["expires_in"])
        
        update_in = MarketplaceCredentialUpdate(
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens.get("refresh_token") or refresh_token,
            expires_at=expires_at
        )
        crud_cred.update_with_encryption(db, db_obj=db_cred, obj_in=update_in)
        
        return new_tokens["access_token"]

# Singleton instance
marketplace_service = MarketplaceService()
