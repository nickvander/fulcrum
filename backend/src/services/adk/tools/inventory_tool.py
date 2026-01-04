"""
Inventory Lookup Tool for ADK Agents.
Allows agents to query stock levels and inventory locations.
"""
from typing import Dict, Any

# Conditional imports for test safety
try:
    from sqlalchemy import func
    from src.db.session import SessionLocal
    from src.models.product import Product
    from src.models.inventory import InventoryItem
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SessionLocal = None
    Product = None
    InventoryItem = None


def get_inventory_status(product_identifier: str) -> Dict[str, Any]:
    """
    Get inventory levels for a product by SKU, barcode, or name.
    
    Args:
        product_identifier: SKU, barcode, or product name to search for.
        
    Returns:
        Dict containing stock levels by location and total quantity.
    """
    if not DB_AVAILABLE:
        return {
            "found": False,
            "error": "Database not available in this context"
        }
        
    db = SessionLocal()
    try:
        # Find product by SKU, barcode, or name
        product = db.query(Product).filter(
            (Product.sku == product_identifier) |
            (Product.barcode_value == product_identifier) |
            (Product.name.ilike(f"%{product_identifier}%"))
        ).first()

        if not product:
            return {
                "found": False,
                "message": f"No product found matching '{product_identifier}'"
            }

        # Get inventory items for this product
        inventory_items = db.query(InventoryItem).filter(
            InventoryItem.product_id == product.id
        ).all()

        locations = []
        total_quantity = 0
        
        for item in inventory_items:
            locations.append({
                "location": item.location,
                "quantity": item.quantity
            })
            total_quantity += item.quantity

        return {
            "found": True,
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "total_quantity": total_quantity,
            "locations": locations,
            "low_stock": total_quantity < 10,  # Configurable threshold
            "out_of_stock": total_quantity == 0
        }
        
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()


def get_low_stock_products(threshold: int = 10) -> Dict[str, Any]:
    """
    Get all products with stock below a threshold.
    
    Args:
        threshold: Minimum quantity below which a product is considered low stock.
        
    Returns:
        Dict containing list of low stock products.
    """
    if not DB_AVAILABLE:
        return {
            "success": False,
            "error": "Database not available in this context"
        }
        
    db = SessionLocal()
    try:
        # Subquery to get total quantity per product
        subquery = db.query(
            InventoryItem.product_id,
            func.sum(InventoryItem.quantity).label('total_qty')
        ).group_by(InventoryItem.product_id).subquery()
        
        # Join with products and filter by threshold
        low_stock = db.query(Product, subquery.c.total_qty).join(
            subquery, Product.id == subquery.c.product_id
        ).filter(subquery.c.total_qty < threshold).all()



        products = []
        for product, qty in low_stock:
            products.append({
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "current_quantity": int(qty),
                "reorder_needed": True
            })

        return {
            "success": True,
            "count": len(products),
            "threshold": threshold,
            "products": products
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


# Tool Definitions for ADK
INVENTORY_STATUS_TOOL = get_inventory_status
LOW_STOCK_TOOL = get_low_stock_products
