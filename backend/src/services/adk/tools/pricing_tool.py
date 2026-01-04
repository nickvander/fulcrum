"""
Pricing Lookup Tool for ADK Agents.
Allows agents to get pricing information and calculate margins.
"""
from typing import Dict, Any

# Conditional imports for test safety
try:
    from src.db.session import SessionLocal
    from src.models.product import Product
    from src.models.supplier import SupplierProduct
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SessionLocal = None
    Product = None


def get_product_pricing(product_identifier: str) -> Dict[str, Any]:
    """
    Get comprehensive pricing information for a product.
    
    Args:
        product_identifier: SKU, barcode, or product name.
        
    Returns:
        Dict containing cost, resale price, margins, and supplier costs.
    """
    if not DB_AVAILABLE:
        return {
            "found": False,
            "error": "Database not available in this context"
        }
        
    db = SessionLocal()
    try:
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

        # Get supplier costs for comparison
        supplier_costs = []
        supplier_products = db.query(SupplierProduct).filter(
            SupplierProduct.product_id == product.id
        ).all()
        
        for sp in supplier_products:
            if sp.cost_price:
                supplier_costs.append({
                    "supplier_id": sp.supplier_id,
                    "cost": float(sp.cost_price)
                })

        cost_price = float(product.cost_price) if product.cost_price else 0
        resale_price = float(product.default_resale_price) if product.default_resale_price else 0
        
        # Calculate margins
        margin = resale_price - cost_price if resale_price and cost_price else 0
        margin_percentage = (margin / resale_price * 100) if resale_price > 0 else 0

        return {
            "found": True,
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "cost_price": cost_price,
            "resale_price": resale_price,
            "margin": round(margin, 2),
            "margin_percentage": round(margin_percentage, 1),
            "supplier_costs": supplier_costs,
            "lowest_supplier_cost": min([s["cost"] for s in supplier_costs]) if supplier_costs else None
        }
        
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()


def calculate_resale_price(cost: float, target_margin_percent: float = 30.0) -> Dict[str, Any]:
    """
    Calculate recommended resale price based on cost and target margin.
    
    Args:
        cost: The product cost price.
        target_margin_percent: Desired profit margin percentage (default 30%).
        
    Returns:
        Dict containing calculated resale price and margin details.
    """
    if cost <= 0:
        return {
            "success": False,
            "error": "Cost must be greater than 0"
        }
    
    # Calculate resale price: cost / (1 - margin_percent/100)
    resale_price = cost / (1 - target_margin_percent / 100)
    margin = resale_price - cost
    
    return {
        "success": True,
        "cost": round(cost, 2),
        "target_margin_percent": target_margin_percent,
        "recommended_resale_price": round(resale_price, 2),
        "margin_amount": round(margin, 2)
    }


# Tool Definitions for ADK
PRICING_TOOL = get_product_pricing
CALCULATE_PRICE_TOOL = calculate_resale_price
