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
                    # No matching product found, create a shell
                    product_id = self._create_product_shell(db, ext_listing)
                    stats["created_product_shell"] += 1
                else:
                    stats["synced"] += 1
                    # Add image if it matched an existing product without an image
                    if ext_listing.image_url:
                        from src.models.product import ProductImage
                        has_image = db.query(ProductImage).filter(ProductImage.product_id == product_id).first()
                        if not has_image:
                            db.add(ProductImage(product_id=product_id, image_path=ext_listing.image_url, is_primary=1, order=0))
                            db.commit()

                db_listing = MarketplaceListing(
                    product_id=product_id,
                    marketplace_id=marketplace_id,
                    external_listing_id=ext_listing.external_id,
                    listing_url=ext_listing.listing_url,
                    status=ext_listing.status,
                    sync_status="SYNCED",
                    marketplace_price=ext_listing.price,
                    original_price=ext_listing.original_price,
                    discount_percentage=ext_listing.discount_percentage,
                    metadata_json=ext_listing.raw_data
                )
                db.add(db_listing)
            else:
                # Existing listing, update fields
                db_listing.status = ext_listing.status
                db_listing.marketplace_price = ext_listing.price
                db_listing.original_price = ext_listing.original_price
                db_listing.discount_percentage = ext_listing.discount_percentage
                db_listing.sync_status = "SYNCED"
                
                # Retroactively add images if missing or only thumbnail exists
                from src.models.product import ProductImage
                existing_images = db.query(ProductImage).filter(ProductImage.product_id == db_listing.product_id).all()
                
                # If we only have the initial thumbnail and there are more images available, refresh them
                if len(existing_images) <= 1 and len(ext_listing.image_urls) > 1:
                    for img in existing_images:
                        db.delete(img)
                    db.flush()
                    
                    for idx, img_url in enumerate(ext_listing.image_urls):
                        db.add(ProductImage(
                            product_id=db_listing.product_id, 
                            image_path=img_url, 
                            is_primary=(1 if idx == 0 else 0), 
                            order=idx
                        ))
                elif not existing_images and ext_listing.image_url:
                    db.add(ProductImage(
                        product_id=db_listing.product_id, 
                        image_path=ext_listing.image_url, 
                        is_primary=1, 
                        order=0
                    ))
                
                # Sync stock proactively
                if ext_listing.available_quantity is not None:
                    from src.services.inventory_service import inventory_service
                    # Get current stock at ML location
                    from src.models.inventory import InventoryItem
                    ml_stock = db.query(InventoryItem).filter(
                        InventoryItem.product_id == db_listing.product_id,
                        InventoryItem.location == "MercadoLibre"
                    ).first()
                    
                    current_qty = ml_stock.quantity if ml_stock else 0
                    if current_qty != ext_listing.available_quantity:
                        adjustment = ext_listing.available_quantity - current_qty
                        inventory_service.adjust_stock(
                            db=db,
                            product_id=db_listing.product_id,
                            adjustment=adjustment,
                            reason="Marketplace sync update",
                            location="MercadoLibre",
                            user_id="system"
                        )
                
                db.commit()
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
        
        # Save images if provided
        from src.models.product import ProductImage
        if listing.image_urls:
            for idx, img_url in enumerate(listing.image_urls):
                img = ProductImage(
                    product_id=product.id,
                    image_path=img_url,
                    is_primary=(1 if idx == 0 else 0),
                    order=idx
                )
                db.add(img)
        elif listing.image_url:
            img = ProductImage(
                product_id=product.id,
                image_path=listing.image_url,
                is_primary=1,
                order=0
            )
            db.add(img)
            
        # Proactively pull in stock
        if listing.available_quantity is not None:
            from src.services.inventory_service import inventory_service
            inventory_service.adjust_stock(
                db=db,
                product_id=product.id,
                adjustment=listing.available_quantity,
                reason="Initial import from MercadoLibre",
                location="MercadoLibre",
                user_id="system"
            )
            
        db.commit()
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
