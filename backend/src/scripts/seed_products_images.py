from src.database import SessionLocal
from src.models.product import Product, ProductImage
from src.models.category import Category
from src.crud.crud_category import slugify
import random


# FP-07 demo taxonomy. Top-level Spanish categories plus two children
# under "Electrónica". The English keys map the legacy seed `cat` strings
# to the Spanish category each demo product is assigned to.
CATEGORY_TREE = [
    {"name": "Electrónica", "sort_order": 0, "children": [
        {"name": "Audio", "sort_order": 0},
        {"name": "Cómputo", "sort_order": 1},
    ]},
    {"name": "Hogar y Cocina", "sort_order": 1, "children": []},
    {"name": "Deportes", "sort_order": 2, "children": []},
    {"name": "Belleza", "sort_order": 3, "children": []},
    {"name": "Juguetes", "sort_order": 4, "children": []},
]

# Map a product's legacy English `cat` string to the Spanish category
# name it should be assigned to. Some Electrónica products are routed to
# the Audio / Cómputo children to exercise the hierarchy.
LEGACY_CAT_TO_CATEGORY = {
    "Electronics": "Electrónica",
    "Home & Garden": "Hogar y Cocina",
    "Sports": "Deportes",
    "Beauty": "Belleza",
    "Toys": "Juguetes",
    # "Fashion" has no top-level home in this small demo tree; those
    # products stay uncategorized (category_id NULL) on purpose.
}

# Product-name -> category-name overrides so specific demo products land
# in the Electrónica children (Audio / Cómputo) instead of the parent.
PRODUCT_NAME_TO_CATEGORY = {
    "Bose QuietComfort 45 Headphones": "Audio",
    "Sonos One Gen 2 Speaker": "Audio",
    "Apple MacBook Pro 16\"": "Cómputo",
    "iPad Pro 12.9\"": "Cómputo",
}


def seed_categories(db) -> dict:
    """Create the Spanish category hierarchy idempotently and return a
    {name: Category} lookup. Safe to re-run."""
    by_name: dict = {}
    for top in CATEGORY_TREE:
        parent = _get_or_create_category(db, top["name"], top["sort_order"], None)
        by_name[top["name"]] = parent
        for child in top.get("children", []):
            node = _get_or_create_category(
                db, child["name"], child["sort_order"], parent.id
            )
            by_name[child["name"]] = node
    db.commit()
    return by_name


def _get_or_create_category(db, name: str, sort_order: int, parent_id):
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        return existing
    cat = Category(
        name=name,
        slug=slugify(name),
        sort_order=sort_order,
        parent_id=parent_id,
        is_active=True,
    )
    db.add(cat)
    db.flush()
    print(f"Created category: {name} ({cat.slug})")
    return cat


def assign_categories_to_products(db, by_name: dict, products_data: list) -> None:
    """Assign category_id to existing demo products based on their legacy
    `cat` mapping (with per-product overrides). Idempotent."""
    for item in products_data:
        product = db.query(Product).filter(Product.name == item["name"]).first()
        if not product:
            continue
        target_name = PRODUCT_NAME_TO_CATEGORY.get(item["name"])
        if target_name is None:
            target_name = LEGACY_CAT_TO_CATEGORY.get(item.get("cat"))
        if target_name is None:
            continue
        category = by_name.get(target_name)
        if category and product.category_id != category.id:
            product.category_id = category.id
            db.add(product)
    db.commit()
    print("Assigned categories to demo products.")

def seed_products_with_images():
    db = SessionLocal()
    try:
        
        if __name__ == "__main__":
            # Nuclear option: Truncate cascade to clear all product-related data
            from sqlalchemy import text
            print("Truncating products and related tables...")
            db.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
            # Also clear invoices since they might point to POs which got deleted
            db.execute(text("TRUNCATE TABLE supplier_invoices RESTART IDENTITY CASCADE"))
            db.commit()
            print("Database cleared successfully.")
        
        # No need for manual deletes anymore
        # db.query(Product).delete() 
        # db.query(ProductImage).delete()
        # db.commit()

        products_data = [
            # Electronics
            {
                "name": "Bose QuietComfort 45 Headphones",
                "cat": "Electronics",
                "price": 329.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Apple MacBook Pro 16\"",
                "cat": "Electronics",
                "price": 2499.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1517336714731-489689fd1ca4?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Canon EOS R5 Camera",
                "cat": "Electronics",
                "price": 3899.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Mechanical Gaming Keyboard RGB",
                "cat": "Electronics",
                "price": 149.99,
                "imgs": [
                    "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Sonos One Gen 2 Speaker",
                "cat": "Electronics",
                "price": 219.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "GoPro Hero 10 Black",
                "cat": "Electronics",
                "price": 399.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Samsung 49\" Odyssey Monitor",
                "cat": "Electronics",
                "price": 1199.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "iPad Pro 12.9\"",
                "cat": "Electronics",
                "price": 1099.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800&auto=format&fit=crop"
                ]
            },
            
            # Fashion
            {
                "name": "Classic Leather Oxford Shoes",
                "cat": "Fashion",
                "price": 120.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Vintage Denim Jacket",
                "cat": "Fashion",
                "price": 85.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1576871337632-b9aef4c17ab9?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1576871337622-98d48d1cf531?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Ray-Ban Aviator Sunglasses",
                "cat": "Fashion",
                "price": 150.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Silk Scarf Floral Print",
                "cat": "Fashion",
                "price": 45.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1584030134671-512f42a6d585?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Minimalist Gold Necklace",
                "cat": "Fashion",
                "price": 250.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1599643478518-17488fbbcd75?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Leather Crossbody Handbag",
                "cat": "Fashion",
                "price": 180.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1590874103328-3607bac5680c?w=800&auto=format&fit=crop"
                ]
            },
            
            # Home & Garden
            {
                "name": "Mid-Century Modern Chair",
                "cat": "Home & Garden",
                "price": 250.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Succulent Plant Collection",
                "cat": "Home & Garden",
                "price": 35.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1459411552884-841db9b3cc2a?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Ceramic Pour Over Coffee Set",
                "cat": "Home & Garden",
                "price": 45.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1520986606214-8b456906c813?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Japanese Chef Knife",
                "cat": "Home & Garden",
                "price": 120.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Luxury Bath Towel Set",
                "cat": "Home & Garden",
                "price": 65.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1583947581924-860b81d41d7a?w=800&auto=format&fit=crop"
                ]
            },
            
            # Sports & Outdoors
            {
                "name": "Yoga Mat Non-Slip Cork",
                "cat": "Sports",
                "price": 45.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1592432678016-e910b452f9a9?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Adjustable Dumbbell Set",
                "cat": "Sports",
                "price": 200.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Hydro Flask Water Bottle",
                "cat": "Sports",
                "price": 35.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1602143407151-a1114130c275?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Camping Tent 4-Person",
                "cat": "Sports",
                "price": 150.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=800&auto=format&fit=crop"
                ]
            },
            
            # Beauty & Health
            {
                "name": "Vitamin C Serum",
                "cat": "Beauty",
                "price": 28.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Organic Face Moisterizer",
                "cat": "Beauty",
                "price": 42.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1571781535073-7b0665c0c976?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Lavender Essential Oil",
                "cat": "Beauty",
                "price": 15.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1608248565278-e60e1f744869?w=800&auto=format&fit=crop"
                ]
            },
            
            # Toys
            {
                "name": "Wooden Building Blocks",
                "cat": "Toys",
                "price": 30.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1587654780291-39c940483731?w=800&auto=format&fit=crop"
                ]
            },
            {
                "name": "Robot Kit for Kids",
                "cat": "Toys",
                "price": 60.00,
                "imgs": [
                    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&auto=format&fit=crop"
                ]
            }
        ]

        print(f"Seeding {len(products_data)} products...")

        for item in products_data:
            # Check if exists
            existing = db.query(Product).filter(Product.name == item["name"]).first()
            if not existing:
                sku_val = f"SKU-{random.randint(1000, 9999)}-{item['cat'][:3].upper()}"
                product = Product(
                    name=item["name"],
                    description=f"High quality {item['name']} for your daily needs. Best in class performance and durability.",
                    default_resale_price=item["price"],
                    sku=sku_val,
                    cost_price=round(item["price"] * 0.6, 2),
                    barcode_value=f"STORE-{sku_val}"
                )
                db.add(product)
                db.flush() # get ID
                
                # Add QR Code
                product.qrcode_value = f"http://localhost:4200/qr/{product.id}"
                db.add(product)
                
                # Add Images
                if "imgs" in item and item["imgs"]:
                    for i, img_url in enumerate(item["imgs"]):
                        image = ProductImage(
                            product_id=product.id,
                            image_path=img_url,
                            is_primary=1 if i == 0 else 0,
                            source="unsplash"
                        )
                        db.add(image)
                elif "img" in item:
                    # Fallback for old structure if any left
                    image = ProductImage(
                        product_id=product.id,
                        image_path=item["img"],
                        is_primary=1,
                        source="mock"
                    )
                    db.add(image)

                print(f"Created: {product.name}")
            else:
                print(f"Skipped (exists): {item['name']}")
        
        db.commit()

        # FP-07: seed the Spanish category taxonomy and assign demo
        # products to their categories. Both steps are idempotent.
        by_name = seed_categories(db)
        assign_categories_to_products(db, by_name, products_data)

        print("Seeding complete.")

    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_products_with_images()
