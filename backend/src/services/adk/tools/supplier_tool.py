"""
Supplier Lookup Tool for ADK Agents.
Allows agents to find suppliers for products and get supplier details.
"""
from typing import Dict, Any

# Conditional imports for test safety
try:
    from src.db.session import SessionLocal
    from src.models.product import Product
    from src.models.supplier import Supplier, SupplierProduct
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SessionLocal = None
    Supplier = None
    SupplierProduct = None


def find_suppliers_for_product(product_identifier: str) -> Dict[str, Any]:
    """
    Find suppliers that can provide a specific product.
    
    Args:
        product_identifier: SKU, barcode, or product name to search for.
        
    Returns:
        Dict containing list of suppliers for the product.
    """
    if not DB_AVAILABLE:
        return {
            "found": False,
            "error": "Database not available in this context"
        }
        
    db = SessionLocal()
    try:
        # Find product first
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

        # Get supplier products for this product
        supplier_products = db.query(SupplierProduct).filter(
            SupplierProduct.product_id == product.id
        ).all()

        suppliers = []
        for sp in supplier_products:
            supplier = db.query(Supplier).filter(Supplier.id == sp.supplier_id).first()
            if supplier:
                suppliers.append({
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "supplier_sku": sp.supplier_sku,
                    "cost_price": float(sp.cost_price) if sp.cost_price else None,
                    "lead_time_days": sp.lead_time_days,
                    "minimum_order_quantity": sp.minimum_order_qty,
                    "is_preferred": sp.is_preferred
                })

        return {
            "found": True,
            "product_id": product.id,
            "product_name": product.name,
            "supplier_count": len(suppliers),
            "suppliers": suppliers,
            "has_preferred_supplier": any(s["is_preferred"] for s in suppliers)
        }
        
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()


def get_supplier_details(supplier_identifier: str) -> Dict[str, Any]:
    """
    Get detailed information about a supplier.
    
    Args:
        supplier_identifier: Supplier name or ID.
        
    Returns:
        Dict containing supplier details and product count.
    """
    if not DB_AVAILABLE:
        return {
            "found": False,
            "error": "Database not available in this context"
        }
        
    db = SessionLocal()
    try:
        # Try to find by ID first, then by name
        supplier = None
        try:
            supplier_id = int(supplier_identifier)
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        except ValueError:
            pass
        
        if not supplier:
            supplier = db.query(Supplier).filter(
                Supplier.name.ilike(f"%{supplier_identifier}%")
            ).first()

        if not supplier:
            return {
                "found": False,
                "message": f"No supplier found matching '{supplier_identifier}'"
            }

        # Count products from this supplier
        product_count = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier.id
        ).count()

        return {
            "found": True,
            "id": supplier.id,
            "name": supplier.name,
            "contact_email": supplier.email,
            "contact_phone": supplier.phone,
            "address": supplier.address,
            "website": supplier.website,
            "product_count": product_count,
            "notes": supplier.notes
        }
        
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }
    finally:
        db.close()


# Tool Definitions for ADK
FIND_SUPPLIERS_TOOL = find_suppliers_for_product
GET_SUPPLIER_TOOL = get_supplier_details
