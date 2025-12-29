from datetime import datetime, date

# In docker, /app is usually in path.


from src.db.session import SessionLocal
from src.crud.crud_purchase_order import purchase_order as crud_po
from src.crud.crud_product import product as crud_product
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderItemCreate, PurchaseOrderUpdate
from src.crud.crud_supplier_product import supplier_product as crud_sp
from src.schemas.product import ProductCreate

def debug_flow():
    db = SessionLocal()
    try:
        print("Starting Debug Flow...")
        
        # 1. Get or Create a Product and Supplier
        # Assuming supplier 1 exists (from previous checks). User said they have POs for supplier 1.
        supplier_id = 1
        
        # Create a temp product
        product_in = ProductCreate(
            name=f"Debug Product {datetime.now().timestamp()}",
            sku=f"DBG-{int(datetime.now().timestamp())}",
            cost_price=10.0,
            price=20.0,
            stock_quantity=0
        )
        product = crud_product.create(db, obj_in=product_in)
        print(f"Created Product: {product.id} {product.name}")
        
        # 2. Create Purchase Order (Draft)
        po_in = PurchaseOrderCreate(
            supplier_id=supplier_id,
            ordered_at=date.today(),
            currency="USD",
            items=[
                PurchaseOrderItemCreate(product_id=product.id, quantity_ordered=10, unit_cost=10.0)
            ]
        )
        po = crud_po.create_with_items(db, obj_in=po_in)
        print(f"Created PO: {po.id}, status: {po.status}")
        
        # 3. Update PO to 'completed' with received date
        # This calls crud_po.update, which triggers _update_supplier_products
        update_data = PurchaseOrderUpdate(
            status="completed",
            received_at=date.today()
        )
        po = crud_po.update(db, db_obj=po, obj_in=update_data)
        print(f"Updated PO: {po.id}, status: {po.status}")
        
        # 4. Check SupplierProduct
        sp_list = crud_sp.get_by_product(db, product_id=product.id)
        if sp_list:
            print(f"SUCCESS: Found {len(sp_list)} SupplierProduct associations.")
            for sp in sp_list:
                print(f" - SP ID: {sp.id}, Cost: {sp.cost_price}, LeadTime: {sp.lead_time_days}")
        else:
            print("FAILURE: No SupplierProduct association found.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_flow()
