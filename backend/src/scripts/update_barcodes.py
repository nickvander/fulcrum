from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.product import Product

def update_barcodes():
    db: Session = SessionLocal()
    try:
        products = db.query(Product).all()
        print(f"Found {len(products)} products to check.")
        
        updated_count = 0
        for product in products:
            changed = False
            
            # Update Barcode Value
            if not product.barcode_value and product.sku:
                # Default strategy for existing products: STORE-{SKU}
                # But to matches user request of "manufacturer" vs "store", 
                # let's assume loose barcodes for now.
                # Actually, the user asked to "update my sample products".
                # I'll generate a Code 128 style "STORE-{SKU}" for them.
                product.barcode_value = f"STORE-{product.sku}"
                changed = True

            # Update QR Code Value - Force update to URL format
            new_qr = f"http://localhost:4200/qr/{product.id}"
            if product.qrcode_value != new_qr:
                product.qrcode_value = new_qr
                changed = True
            
            if changed:
                db.add(product)
                updated_count += 1
        
        db.commit()
        print(f"Successfully updated {updated_count} products.")
        
    except Exception as e:
        print(f"Error updating barcodes: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_barcodes()
