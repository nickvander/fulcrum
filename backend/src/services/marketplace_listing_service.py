from typing import Optional, Dict
from sqlalchemy.orm import Session
from src.crud import crud_product, crud_marketplace
from src.models.marketplace import MarketplaceListing
from src.schemas.product import ProductCreate
from src.services.marketplace_service import marketplace_service
from src.services.marketplaces.base import ListingData

class MarketplaceListingService:
    """
    Service to manage the mapping and synchronization of product listings
    between Fulcrum and external marketplaces.
    """

    async def import_marketplace_listings(self, db: Session, marketplace_id: int, user_id: int) -> Dict[str, int]:
        """
        Fetches all listings from a marketplace and synchronizes them with Fulcrum.
        """
        db_marketplace = crud_marketplace.marketplace.get(db, id=marketplace_id)
        if not db_marketplace:
            raise ValueError(f"Marketplace with ID {marketplace_id} not found.")

        # Get credentials for this user and marketplace
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
        db_cred = crud_cred.get_by_marketplace(db, user_id=user_id, marketplace_id=marketplace_id)
        if not db_cred:
            raise ValueError(f"No credentials found for marketplace {db_marketplace.name}")

        token = await marketplace_service.get_valid_access_token(db, db_cred.id)
        
        connector = marketplace_service.get_connector(db_marketplace.name)
        external_listings = await connector.fetch_all_listings(access_token=token)

        stats = {"synced": 0, "created_product_shell": 0, "orphaned": 0}

        for ext_listing in external_listings:
            # Check if listing already exists in Fulcrum
            db_listing = db.query(MarketplaceListing).filter(
                MarketplaceListing.marketplace_id == marketplace_id,
                MarketplaceListing.external_listing_id == ext_listing.external_id
            ).first()

            if not db_listing:
                # New listing found on marketplace
                product_id = self._find_matching_product(db, ext_listing.sku)
                
                if not product_id:
                    # No matching product found, create a shell?
                    # For now, let's just mark as orphaned if no SKU match, 
                    # but we could create a product shell here if the user wants.
                    # Let's implement the 'auto-create' logic.
                    product_id = self._create_product_shell(db, ext_listing)
                    stats["created_product_shell"] += 1
                else:
                    stats["synced"] += 1

                db_listing = MarketplaceListing(
                    product_id=product_id,
                    marketplace_id=marketplace_id,
                    external_listing_id=ext_listing.external_id,
                    listing_url=ext_listing.listing_url,
                    status=ext_listing.status,
                    sync_status="SYNCED",
                    marketplace_price=ext_listing.price,
                    metadata_json=ext_listing.raw_data
                )
                db.add(db_listing)
            else:
                # Existing listing, update status/price
                db_listing.status = ext_listing.status
                db_listing.marketplace_price = ext_listing.price
                db_listing.sync_status = "SYNCED"
                stats["synced"] += 1

        db.commit()
        return stats

    def _find_matching_product(self, db: Session, sku: Optional[str]) -> Optional[int]:
        """Finds an internal product by SKU."""
        if not sku:
            return None
        product = crud_product.product.get_by_sku(db, sku=sku)
        return product.id if product else None

    def _create_product_shell(self, db: Session, listing: ListingData) -> int:
        """Creates a minimal product shell from marketplace data."""
        product_in = ProductCreate(
            name=listing.title,
            sku=listing.sku or f"AUTO-{listing.external_id}",
            description=f"Imported from marketplace: {listing.title}",
            default_resale_price=listing.price or 0.0,
            cost_price=0.0
        )
        product = crud_product.product.create(db, obj_in=product_in)
        return product.id

    async def publish_to_marketplace(self, db: Session, product_id: int, marketplace_id: int, user_id: int) -> MarketplaceListing:
        """
        Publishes a Fulcrum product to a marketplace and creates the mapping.
        """
        product = crud_product.product.get(db, id=product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        db_marketplace = crud_marketplace.marketplace.get(db, id=marketplace_id)
        if not db_marketplace:
            raise ValueError(f"Marketplace with ID {marketplace_id} not found.")

        # Get credentials
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
        db_cred = crud_cred.get_by_marketplace(db, user_id=user_id, marketplace_id=marketplace_id)
        if not db_cred:
            raise ValueError(f"No credentials found for marketplace {db_marketplace.name}")

        token = await marketplace_service.get_valid_access_token(db, db_cred.id)

        # Check if already listed
        existing = db.query(MarketplaceListing).filter(
            MarketplaceListing.product_id == product_id,
            MarketplaceListing.marketplace_id == marketplace_id
        ).first()
        if existing:
            return existing

        connector = marketplace_service.get_connector(db_marketplace.name)
        
        # Prepare data for publishing
        product_data = {
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "price": product.default_resale_price
        }
        
        external_id = await connector.publish_listing(product_data, access_token=token)
        
        db_listing = MarketplaceListing(
            product_id=product_id,
            marketplace_id=marketplace_id,
            external_listing_id=external_id,
            status="PUBLISHED",
            sync_status="SYNCED"
        )
        db.add(db_listing)
        db.commit()
        db.refresh(db_listing)
        return db_listing

# Singleton instance
marketplace_listing_service = MarketplaceListingService()
