from src.crud import crud_product
from src.schemas.product import ProductCreate
from src.database import SessionLocal

# Init DB Session
def test_barcode_integration():
    db = SessionLocal()

    try:
        print("Testing Barcode Creation & Lookup...")
        
        # Clean up previous test
        existing = crud_product.product.get_by_sku(db, sku="TEST-BARCODE-LOOKUP")
        if existing:
            crud_product.product.remove(db, id=existing.id)
            db.commit()

        # Create Product
        product_in = ProductCreate(
            name="Test Barcode Product",
            sku="TEST-BARCODE-LOOKUP",
            default_resale_price=10.0,
            cost_price=5.0
        )
        
        # This should trigger barcode generation and value saving
        product = crud_product.product.create(db, obj_in=product_in)
        
        print(f"Product Created: ID={product.id}, SKU={product.sku}")
        print(f"Barcode Value: {product.barcode_value}")
        print(f"QR Value: {product.qrcode_value}")

        # Verify Values
        assert product.barcode_value == "TEST-BARCODE-LOOKUP"
        assert product.qrcode_value == f"fulcrum-product:{product.id}"

        # Verify Lookup
        print("Testing Lookup...")
        found_by_sku = crud_product.product.get_by_barcode(db, barcode_value="TEST-BARCODE-LOOKUP")
        assert found_by_sku.id == product.id
        print("Found by Barcode Value (SKU): OK")

        found_by_qr = crud_product.product.get_by_barcode(db, barcode_value=f"fulcrum-product:{product.id}")
        assert found_by_qr.id == product.id
        print("Found by QR Value: OK")
        
        print("SUCCESS: Barcode/QR integration verified.")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()
