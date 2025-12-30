import sys
import os
import random
from datetime import datetime, timedelta

import requests

# Try to import src, if not found, add ../backend to path (local dev case)
try:
    current_dir = os.path.dirname(__file__)
    backend_path = os.path.join(current_dir, '../backend')
    if os.path.exists(backend_path):
        sys.path.append(backend_path)
except NameError:
    # __file__ is not defined (e.g. running via stdin/pipe)
    # Assume we are in a correct environment (like Docker /app)
    pass

from src.database import SessionLocal
from src.crud.crud_user import user as crud_user
from src.schemas.user import UserCreate, UserType

API_URL = "http://localhost:8000/api/v1"
TOKEN = None

# Sample data
adjectives = ["Ergonomic", "Wireless", "Premium", "Sleek", "Durable", "Compact", "Smart", "Eco-friendly", "Vintage", "Modern"]
nouns = ["Mouse", "Keyboard", "Monitor", "Stand", "Headphones", "Speaker", "Hub", "Charger", "Lamp", "Desk"]
brands = ["Logitech", "Dell", "Apple", "Anker", "Sony", "Samsung", "LG", "HP"]

def ensure_admin_user():
    db = SessionLocal()
    try:
        user = crud_user.get_by_email(db, email="admin@example.com")
        if not user:
            print("Admin user not found. Creating...")
            user_in = UserCreate(
                email="admin@example.com",
                password="password",
                first_name="Admin",
                last_name="User",
                user_type=UserType.ADMIN,
                is_superuser=True
            )
            user = crud_user.create(db, obj_in=user_in)
            print("Admin user created.")
    except Exception as e:
        print(f"Error checking/creating admin user: {e}")
    finally:
        db.close()

def login():
    global TOKEN
    try:
        data = {"username": "admin@example.com", "password": "SecurePass123!"}
        resp = requests.post(f"{API_URL}/users/login/access-token", data=data) 
        if resp.status_code == 200:
            TOKEN = resp.json()['access_token']
            print("Successfully logged in.")
        else:
            print(f"Login failed: {resp.text}")
    except Exception as e:
        print(f"Login error: {e}")

def get_headers():
    if TOKEN:
        return {"Authorization": f"Bearer {TOKEN}"}
    return {}

def get_existing_products():
    try:
        response = requests.get(f"{API_URL}/products/?limit=100", headers=get_headers())
        if response.status_code == 200:
            return response.json()['data']
    except Exception as e:
        print(f"Error fetching products: {e}")
    return []

def create_product():
    name = f"{random.choice(adjectives)} {random.choice(nouns)} {random.randint(100, 999)}"
    price = round(random.uniform(20.0, 500.0), 2)
    cost = round(price * 0.6, 2)
    stock = random.randint(0, 50)
    
    payload = {
        "name": name,
        "description": f"A great {name.lower()} for your setup.",
        "sku": f"SKU-{random.randint(10000, 99999)}",
        "default_resale_price": price,
        "cost_price": cost,
        "stock_quantity": stock,
        "brand": random.choice(brands),
        "category": "Electronics",
        "is_bundle": False
    }
    
    try:
        response = requests.post(f"{API_URL}/products/", json=payload, headers=get_headers())
        if response.status_code in [200, 201]:
            print(f"Created product: {name}")
            return response.json()
        else:
            print(f"Failed to create product: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def create_bundle(components):
    name = f"Ultimate {random.choice(adjectives)} Bundle"
    price = sum(c['default_resale_price'] for c in components) * 0.9 # 10% discount
    
    bundle_components = []
    for comp in components:
        bundle_components.append({
            "component_id": comp['id'],
            "quantity": 1
        })

    payload = {
        "name": name,
        "description": "Everything you need in one box.",
        "sku": f"BNDL-{random.randint(1000, 9999)}",
        "default_resale_price": round(price, 2),
        "is_bundle": True,
        "bundle_components": bundle_components
    }

    try:
        response = requests.post(f"{API_URL}/products/", json=payload, headers=get_headers())
        if response.status_code in [200, 201]:
            print(f"Created bundle: {name}")
        else:
            print(f"Failed to create bundle: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def get_or_create_marketplace(name):
    try:
        # Try to find existing
        response = requests.get(f"{API_URL}/marketplace/", headers=get_headers())
        if response.status_code == 200:
            marketplaces = response.json()
            for m in marketplaces:
                if m['name'] == name:
                    return m['id']
        
        # Create new
        payload = {"name": name}
        response = requests.post(f"{API_URL}/marketplace/", json=payload, headers=get_headers())
        if response.status_code in [200, 201]:
            print(f"Created marketplace: {name}")
            return response.json()['id']
    except Exception as e:
        print(f"Error managing marketplace {name}: {e}")
    return None

def create_listing(product_id, marketplace_id, price):
    payload = {
        "product_id": product_id,
        "marketplace_id": marketplace_id,
        "external_listing_id": f"EXT-{random.randint(10000, 99999)}",
        "listing_url": f"https://example.com/p/{product_id}",
        "status": "ACTIVE",
        "marketplace_price": price
    }
    try:
        requests.post(f"{API_URL}/marketplace/listings/", json=payload, headers=get_headers())
    except Exception:
        # Ignore duplicate listing errors
        pass

def create_campaign(products):
    if not products:
        return
        
    name = f"Summer Sale {random.randint(2025, 2030)}"
    product_ids = [p['id'] for p in products]
    
    payload = {
        "name": name,
        "status": "active",
        "start_date": "2025-06-01",
        "end_date": "2025-08-31",
        "is_smart_boost": True,
        "boost_reason": "High demand season",
        "product_ids": product_ids
    }
    
    try:
        # Create campaign
        resp = requests.post(f"{API_URL}/marketing/campaigns/", json=payload, headers=get_headers())
        if resp.status_code in [200, 201]:
            print(f"Created campaign: {name} with {len(product_ids)} products")
        else:
            print(f"Failed to create campaign: {resp.text}")
            
    except Exception as e:
        print(f"Error creating campaign: {e}")

def create_quick_post(product):
    topics = ["Flash Sale!", "Back within Stock", "New Review", "Feature Highlight", "Limited Time Offer"]
    channels = ["instagram", "facebook", "twitter", "email"]
    
    topic = random.choice(topics)
    channel = random.choice(channels)
    
    # Calculate a date
    days_ago = random.randint(0, 10)
    scheduled_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
    
    payload = {
        "name": f"{topic} - {product['name']}",
        "channel_type": "social" if channel in ["instagram", "facebook", "twitter"] else "email",
        "content_subject": f"{topic}: {product['name']}",
        "content_body": f"Check out the {product['name']}! It's amazing.",
        "status": "published",
        "scheduled_at": scheduled_at,
        "published_at": scheduled_at,
        "product_ids": [product['id']]
    }
    
    try:
        resp = requests.post(f"{API_URL}/marketing/quick-posts", json=payload, headers=get_headers())
        if resp.status_code in [200, 201]:
            print(f"Created quick post for product: {product['name']}")
        else:
            print(f"Failed to create quick post: {resp.text}")
    except Exception as e:
        print(f"Error creating quick post: {e}")

if __name__ == "__main__":
    print("Starting full seed...")
    login()
    
    # Ensure Marketplaces exist
    amazon_id = get_or_create_marketplace("Amazon")
    ml_id = get_or_create_marketplace("MercadoLibre")

    # Ensure Suppliers exist
    def create_supplier(name):
        try:
            # Check if exists (simple check via API if possible, or just create and ignore error)
            # For simplicity in this script, we'll try to create
            payload = {
                "name": name,
                "email": f"contact@{name.lower().replace(' ', '')}.com",
                "phone": "555-0100",
                "country": "USA"
            }
            resp = requests.post(f"{API_URL}/suppliers/", json=payload, headers=get_headers())
            if resp.status_code in [200, 201]:
                print(f"Created supplier: {name}")
                return resp.json()['id']
            elif resp.status_code == 400:
                # Already exists? Not ideal but okay for seed
                 pass
        except Exception as e:
            print(f"Error creating supplier: {e}")
        return None

    suppliers = ["TechDistro Inc", "Global Gadgets", "Direct Components"]
    supplier_ids = []
    for s in suppliers:
        sid = create_supplier(s)
        if sid:
            supplier_ids.append(sid)
    
    # 1. Get existing products or create new ones
    products = get_existing_products()
    print(f"Found {len(products)} existing products.")
    
    products_needed = 15 - len(products)
    if products_needed > 0:
        print(f"Creating {products_needed} new products...")
        for _ in range(products_needed):
            # Pass a random supplier if we have them
            # Note: create_product function needs update to accept supplier_id
            # For now, we'll just create them without updating the function signature logic inlining here involves too much change
            # Let's simple update the function above or doing it here...
            # Actually, let's just create product as is.
            p = create_product()
            if p:
                products.append(p)
    
    # 2. Add listings to products that don't have them (roughly)
    for p in products:
        if amazon_id and random.random() > 0.3:
            create_listing(p['id'], amazon_id, p['default_resale_price'])
        if ml_id and random.random() > 0.5:
            create_listing(p['id'], ml_id, p['default_resale_price'])

    # 3. Create a few bundles if we have enough products
    if len(products) >= 3:
        # Only create if we think we might need more (simple check: assume we want some bundles)
        # For now, just create one to be safe, duplicates might fail or we just add more
        create_bundle(random.sample(products, 2))
        
    # 4. Create campaigns (Active)
    # Pick 5 random products for a campaign
    if len(products) >= 5:
        campaign_products = random.sample(products, 5)
        create_campaign(campaign_products)

    # 5. Create Quick Posts
    # Create quick posts for 5 random products
    if len(products) > 0:
        quick_post_products = random.sample(products, min(len(products), 5))
        for p in quick_post_products:
            create_quick_post(p)
            
    print("Seed complete.")
