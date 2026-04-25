# Database Seeding Guide

This guide explains how to seed your database with test data for development and
testing purposes.

## Quick Start

```bash
# Start the backend services
docker compose up -d

# Run the seed script (inside Docker)
docker compose exec backend python -m src.scripts.seed_full
```

## Available Seed Scripts

### Comprehensive Seeding (`seed_full.py`)

**Recommended for fresh installs.** This script orchestrates the seeding of:

- **Users**:
  - `admin@example.com` (Password: `SecurePass123!`) - **Superuser**
- **Products**:
  - 30+ items across Electronics, Fashion, Home, Sports
- **Suppliers**:
  - Global Electronics Ltd
  - Fashion Forward Inc
  - Home Essentials Co
- **Purchase Orders**:
  - 1 Completed PO ($5,000)
  - 1 Draft PO ($1,200.50)
- **Expenses**:
  - Office Supplies (One-time)
  - Software Subscription (Recurring Monthly)
- **Marketing**:
  - **Connectors**: Instagram, Newsletter Service
  - **Campaign**: "Summer Sale 2025" (Scheduled)
  - **Events**: Teaser Post (IG), Launch Blast (Email)

```bash
# From Docker
docker compose exec backend python -m src.scripts.seed_full
```

### Products with Images (`seed_products_images.py`)

Seeds the database with 30+ realistic products from various categories, complete
with product images from Unsplash CDN.

**Categories included:**

- Electronics (headphones, laptops, cameras)
- Home & Garden (furniture, kitchen items)
- Fashion (accessories, apparel)
- Sports & Outdoors (equipment, gear)

**What gets seeded:**

- Product names with realistic descriptions
- SKUs and barcodes
- Prices and cost prices
- Multiple product images per product
- Stock quantities

### Running the Script

```bash
# From Docker
docker compose exec backend python -m src.scripts.seed_products_images

# Or directly (if running locally)
cd backend && python -m src.scripts.seed_products_images
```

## Image Storage Best Practices

### External URLs (Recommended for Development)

The seed script uses **Unsplash CDN URLs** for product images. This approach:

✅ **Advantages:**

- No large files to store in git
- Fast seed script execution
- Always-fresh, high-quality images
- Reduces repository size

⚠️ **Considerations:**

- Requires internet connection
- External service dependency
- URLs may change over time

### Local Image Files (For Offline/Production)

If you need local images:

1. Download images to `backend/static/images/`
2. Update seed script to use local paths
3. Add to `.gitignore` if large

```python
# Example: Using local paths
"imgs": [
    "/static/images/products/headphones-1.jpg",
    "/static/images/products/headphones-2.jpg"
]
```

## Git Best Practices for Seed Data

### What to Commit

✅ **Do commit:**

- Seed scripts (`src/scripts/*.py`)
- Small sample data files (< 100KB)
- Configuration for external URLs
- README/documentation

❌ **Don't commit:**

- Large image files (> 1MB each)
- Binary assets (use Git LFS or external CDN)
- Database dumps
- Credentials or API keys

### Using Git LFS for Large Files

If you must store images locally:

```bash
# Install Git LFS
git lfs install

# Track image files
git lfs track "*.jpg" "*.png" "*.webp"

# Commit the .gitattributes
git add .gitattributes
git commit -m "Configure Git LFS for images"
```

## Resetting the Database

To clear existing data before seeding:

```bash
# Truncate all tables (DESTRUCTIVE!)
docker compose exec backend python -c "
from src.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
db.execute(text('TRUNCATE TABLE products RESTART IDENTITY CASCADE'))
db.commit()
"

# Then run seed script
docker compose exec backend python -m src.scripts.seed_full
```

## Creating Custom Seed Scripts

Use this template for new seed scripts:

```python
# backend/src/scripts/seed_example.py
from src.database import SessionLocal
from src.models.your_model import YourModel

def seed_data():
    db = SessionLocal()
    try:
        # Your seeding logic here
        item = YourModel(name="Example")
        db.add(item)
        db.commit()
        print(f"Created: {item.name}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
```

## Related Documentation

- [Getting Started](../getting-started/index.rst) - Initial project setup
- [Testing Guide](./testing.md) - Running tests with seeded data
