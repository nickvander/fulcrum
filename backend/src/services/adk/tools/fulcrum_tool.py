"""
Fulcrum Internal Product Tool for ADK Agents.
Allows agents to check if products already exist in the database.
"""
from typing import Dict, Any
from sqlalchemy import or_
from src.db.session import SessionLocal
from src.models.product import Product

def find_internal_product(sku_or_name: str) -> Dict[str, Any]:
    """
    Check if a product exists in the Fulcrum database by SKU or exact Name.
    Useful for seeing if an identified product is already in the system.
    
    Args:
        sku_or_name: The SKU string or Product Name to search for.
        
    Returns:
        Dict containing found status and basic info if found.
    """
    db = SessionLocal()
    try:
        # Search for SKU match OR Name match (case-insensitive fuzzy)
        product = db.query(Product).filter(
            or_(
                Product.sku == sku_or_name,
                Product.name.ilike(f"%{sku_or_name}%"),
                Product.barcode_value == sku_or_name
            )
        ).first()

        if product:
            return {
                "found": True,
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "brand": product.brand,
                "price": product.default_resale_price,
                "specs": {
                   "width": product.width,
                   "height": product.height,
                   "depth": product.depth,
                   "weight": product.weight
                }
            }
        else:
            return {
                "found": False,
                "message": f"No product found matching '{sku_or_name}'"
            }
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()

# Tool Definition for ADK
TOOL_DEFINITION = find_internal_product
