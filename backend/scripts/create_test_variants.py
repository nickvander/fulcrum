from src.database import SessionLocal
from src.crud.crud_product import product as crud_product
from src.crud.crud_product_variant import product_variant as crud_variant
from src.schemas.product import ProductCreate
from src.schemas.product_variant import ProductVariantCreate

def create_test_product_with_variants():
    db = SessionLocal()
    try:
        # Create a product
        p_in = ProductCreate(
            name="Ecotapa Multivariant",
            sku="ECO-MULTI-TEST",
            description="Test product with variants",
            default_resale_price=150.0,
            cost_price=50.0,
            category="Home",
            is_bundle=False
        )
        
        # Check if already exists
        p = crud_product.get_by_sku(db, sku=p_in.sku)
        if not p:
            p = crud_product.create(db, obj_in=p_in)
            print(f"Created product {p.name} (ID: {p.id})")
        else:
            print(f"Product {p.name} already exists (ID: {p.id})")
            
        # Create variants
        variants_to_create = [
            {"name": "Red", "sku": "ECO-RED", "price": 55.0},
            {"name": "Blue", "sku": "ECO-BLUE", "price": 55.0},
            {"name": "Green", "sku": "ECO-GREEN", "price": 60.0}
        ]
        
        for v_data in variants_to_create:
            # Check if variant exists
            existing_v = db.query(crud_variant.model).filter(crud_variant.model.sku == v_data["sku"]).first()
            if not existing_v:
                v_in = ProductVariantCreate(
                    product_id=p.id,
                    name=v_data["name"],
                    sku=v_data["sku"],
                    price=v_data["price"],
                    cost_price=p.cost_price
                )
                v = crud_variant.create(db, obj_in=v_in)
                print(f"Created variant {v.name} for product {p.id}")
            else:
                print(f"Variant {v_data['sku']} already exists.")
        
    finally:
        db.close()

if __name__ == "__main__":
    create_test_product_with_variants()
