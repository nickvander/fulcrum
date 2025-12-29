from src.database import SessionLocal
from src.models.product import Product
from src.models.inventory import InventoryItem
from src.models.order import SalesOrder, SalesOrderItem
from src.models.store_settings import StoreSettings
from src.models.product_inventory_settings import ProductInventorySettings
from datetime import datetime, timedelta

def seed_data():
    db = SessionLocal()
    try:
        print("Seeding Inventory Data...")
        
        # 1. Reset Global Settings to default (30)
        settings = db.query(StoreSettings).first()
        if not settings:
            settings = StoreSettings()
            db.add(settings)
        settings.low_inventory_days_default = 30
        db.commit()
        
        # 2. Create Products
        products_data = [
            {"name": "Healthy Stock Item", "sku": "SEED-HEALTHY", "price": 50.0},
            {"name": "Low Stock Item", "sku": "SEED-LOW", "price": 50.0},
            {"name": "Custom Threshold Item", "sku": "SEED-CUSTOM", "price": 50.0},
        ]
        
        created_products = []
        for p_data in products_data:
            p = db.query(Product).filter(Product.sku == p_data["sku"]).first()
            if not p:
                p = Product(
                    name=p_data["name"],
                    sku=p_data["sku"],
                    default_resale_price=p_data["price"],
                    cost_price=20.0
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            created_products.append(p)
        
        healthy = created_products[0]
        low = created_products[1]
        custom = created_products[2]
        
        # 3. Create Sales History (Velocity)
        # Aim for velocity of 1 unit/day for simplicity
        # Create 30 orders in last 30 days for each
        
        # Check if orders exist to avoid dups
        existing_orders = db.query(SalesOrder).filter(SalesOrder.status == "COMPLETED").count()
        if existing_orders < 10:
            for p in created_products:
                for i in range(30):
                    order = SalesOrder(
                        status="COMPLETED",
                        created_at=datetime.utcnow() - timedelta(days=i), # Distributed history
                        total_price=50.0,
                        source="FULCRUM"
                    )
                    db.add(order)
                    db.flush()
                    
                    item = SalesOrderItem(
                        order_id=order.id,
                        product_id=p.id,
                        quantity=1,
                        price_per_unit=50.0
                    )
                    db.add(item)
            db.commit()
            print("Created sales history.")
        
        # 4. Set Inventory
        # Healthy: 60 units (60 days > 30)
        # Low: 10 units (10 days < 30)
        # Custom: 45 units (45 days > 30 default, but we will set custom threshold to 60)
        
        def set_stock(pid, qty):
            inv = db.query(InventoryItem).filter(InventoryItem.product_id == pid).first()
            if not inv:
                inv = InventoryItem(product_id=pid, quantity=qty, location="default")
            else:
                inv.quantity = qty
            db.add(inv)
                
        set_stock(healthy.id, 60)
        set_stock(low.id, 10)
        set_stock(custom.id, 45)
        
        # 5. Set Custom Threshold
        # Set custom threshold to 60 days. Current stock 45 days. Should be flagged as LOW.
        cust_settings = db.query(ProductInventorySettings).filter(ProductInventorySettings.product_id == custom.id).first()
        if not cust_settings:
            cust_settings = ProductInventorySettings(product_id=custom.id, low_inventory_days_threshold=60)
            db.add(cust_settings)
        else:
            cust_settings.low_inventory_days_threshold = 60
            db.add(cust_settings)
            
        db.commit()
        # 6. Seed Supplier Products (for Supplier ID 2 if exists)
        # We know from previous steps user has Supplier 2.
        from src.models.supplier_product import SupplierProduct
        
        # Ensure supplier 2 exists or use 1
        supplier_id = 2
        
        # Link Healthy Item to Supplier 2
        sp1 = db.query(SupplierProduct).filter(
            SupplierProduct.product_id == healthy.id,
            SupplierProduct.supplier_id == supplier_id
        ).first()
        
        if not sp1:
            sp1 = SupplierProduct(
                product_id=healthy.id,
                supplier_id=supplier_id,
                supplier_sku="SUP-HEALTHY-001",
                cost_price=45.0,
                is_primary=True,
                lead_time_days=7
            )
            db.add(sp1)
            
        # Link Low Stock Item to Supplier 2
        sp2 = db.query(SupplierProduct).filter(
            SupplierProduct.product_id == low.id,
            SupplierProduct.supplier_id == supplier_id
        ).first()
        
        if not sp2:
            sp2 = SupplierProduct(
                product_id=low.id,
                supplier_id=supplier_id,
                supplier_sku="SUP-LOW-001",
                cost_price=45.0,
                is_primary=True,
                lead_time_days=3
            )
            db.add(sp2)

        db.commit()
        print("Seeding Complete!")
        print(f"Products seeded: {healthy.sku}, {low.sku}, {custom.sku}")
        print(f"Linked products to Supplier {supplier_id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
