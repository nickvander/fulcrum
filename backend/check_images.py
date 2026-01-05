from src.database import SessionLocal
from src.models.product import Product, ProductImage

db = SessionLocal()
try:
    products = db.query(Product).limit(5).all()
    print(f"Found {len(products)} products sample.")
    for p in products:
        print(f"Product: {p.name} (ID: {p.id})")
        images = db.query(ProductImage).filter(ProductImage.product_id == p.id).all()
        print(f"  Images ({len(images)}):")
        for img in images:
            print(f"    - ID: {img.id}, Path: {img.image_path}, Primary: {img.is_primary}")
            
    count = db.query(ProductImage).count()
    print(f"\nTotal images in DB: {count}")
finally:
    db.close()
