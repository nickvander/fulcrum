from src.database import SessionLocal
from src.models.marketplace import Marketplace, MarketplaceListing
from src.models.product import Product

def seed_marketplaces():
    db = SessionLocal()
    try:
        # 1. Create Marketplaces if they don't exist
        amazon = db.query(Marketplace).filter(Marketplace.name == "Amazon").first()
        if not amazon:
            amazon = Marketplace(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
            db.add(amazon)
        
        ml = db.query(Marketplace).filter(Marketplace.name == "MercadoLibre").first()
        if not ml:
            ml = Marketplace(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
            db.add(ml)
        
        db.commit()
        db.refresh(amazon)
        db.refresh(ml)
        
        # 2. Add some dummy listings if there are products
        product = db.query(Product).first()
        if product:
            existing_listing = db.query(MarketplaceListing).filter(
                MarketplaceListing.product_id == product.id,
                MarketplaceListing.marketplace_id == amazon.id
            ).first()
            
            if not existing_listing:
                listing = MarketplaceListing(
                    product_id=product.id,
                    marketplace_id=amazon.id,
                    external_listing_id="B00EXAMPLE",
                    listing_url="https://amazon.com/dp/B00EXAMPLE",
                    status="active",
                    sync_status="IN_SYNC",
                    marketplace_price=product.default_resale_price or 10.0
                )
                db.add(listing)
                db.commit()
                print(f"Created dummy listing for product {product.id}")
        
        print(f"Seeded Amazon (ID: {amazon.id}) and MercadoLibre (ID: {ml.id})")
    finally:
        db.close()

if __name__ == "__main__":
    seed_marketplaces()
