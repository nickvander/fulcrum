
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.models.product import Product
from src.models.supplier import Supplier
from src.models.order import SalesOrder, SalesOrderItem, OrderSource
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderItemCreate
from src.services.inventory_service import inventory_service
from src.crud import crud_purchase_order, crud_supplier_product

def create_product(db: Session, sku: str = "TEST- SKU-1"):
    product = Product(name="Test Product", sku=sku, description="Test Desc", cost_price=10.0, default_resale_price=20.0, is_bundle=False)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def create_supplier(db: Session, name: str = "Test Supplier"):
    supplier = Supplier(name=name, email="test@test.com", contact_person="Test")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@pytest.mark.db
def test_sales_velocity_calculation(db: Session):
    product = create_product(db, sku="VEL-001")
    
    # Create orders within window (last 30 days)
    # Order 1: 5 units, 5 days ago
    order1 = SalesOrder(
        status="COMPLETED",
        total_price=100.0,
        source=OrderSource.FULCRUM,
        created_at=datetime.utcnow() - timedelta(days=5),
        external_order_id="EXT-1"
    )
    db.add(order1)
    db.commit()
    
    item1 = SalesOrderItem(
        order_id=order1.id,
        product_id=product.id,
        quantity=5,
        price_per_unit=20.0
    )
    db.add(item1)
    
    # Order 2: 10 units, 10 days ago
    order2 = SalesOrder(
        status="SHIPPED",
        total_price=200.0,
        source=OrderSource.FULCRUM,
        created_at=datetime.utcnow() - timedelta(days=10),
        external_order_id="EXT-2"
    )
    db.add(order2)
    db.commit() # Flush items
    
    item2 = SalesOrderItem(
        order_id=order2.id,
        product_id=product.id,
        quantity=10,
        price_per_unit=20.0
    )
    db.add(item2)
    
    # Order 3: 100 units, but OLD (60 days ago) - Should be ignored
    order3 = SalesOrder(
        status="COMPLETED",
        total_price=2000.0,
        source=OrderSource.FULCRUM,
        created_at=datetime.utcnow() - timedelta(days=60),
        external_order_id="EXT-3"
    )
    db.add(order3)
    db.commit()
    
    item3 = SalesOrderItem(
        order_id=order3.id,
        product_id=product.id,
        quantity=100,
        price_per_unit=20.0
    )
    db.add(item3)
    
    db.commit()
    
    # Calculate Velocity (30 days)
    # Total Sold = 5 + 10 = 15
    # Window = 30
    # Velocity = 0.5
    
    velocity = inventory_service.calculate_sales_velocity(db, product.id, days=30)
    assert velocity == 0.5
    
    # Days of Inventory
    # Add stock first
    inventory_service.adjust_stock(db, product.id, 15, location="default", reason="Initial")
    db.commit() # Ensure stock is saved for query
    
    doi = inventory_service.calculate_days_of_inventory(db, product.id)
    # 15 / 0.5 = 30 days
    assert doi == 30.0

    assert doi == 30.0


@pytest.mark.db
def test_auto_associate_supplier_product(db: Session):
    product = create_product(db, sku="SUP-ASSOC-001")
    supplier = create_supplier(db, name="Auto Supplier")
    
    # Create PO
    po_in = PurchaseOrderCreate(
        supplier_id=supplier.id,
        status="ordered",
        items=[
            PurchaseOrderItemCreate(product_id=product.id, quantity_ordered=10, unit_cost=15.0)
        ]
    )
    crud_purchase_order.purchase_order.create_with_items(db, obj_in=po_in)
    
    sp = crud_supplier_product.supplier_product.get_by_product_and_supplier(db, product_id=product.id, supplier_id=supplier.id)
    assert sp is not None
    assert sp.cost_price == 15.0
    assert sp.lead_time_days == 0 # No dates yet


@pytest.mark.db
def test_lead_time_calculation(db: Session):
    product = create_product(db, sku="LEAD-TIME-001")
    supplier = create_supplier(db, name="Lead Time Supplier")
    
    # Ordered 10 days ago
    ordered_at = datetime.utcnow() - timedelta(days=10)
    # Received Today
    received_at = datetime.utcnow()
    
    po_in = PurchaseOrderCreate(
        supplier_id=supplier.id,
        status="ordered",
        ordered_at=ordered_at,
        items=[
            PurchaseOrderItemCreate(product_id=product.id, quantity_ordered=10, unit_cost=50.0)
        ]
    )
    po = crud_purchase_order.purchase_order.create_with_items(db, obj_in=po_in)
    
    # Simulate Receive
    update_data = {
        "status": "completed",
        "received_at": received_at
    }
    
    crud_purchase_order.purchase_order.update(db, db_obj=po, obj_in=update_data)
    
    # Check Supplier Product
    sp = crud_supplier_product.supplier_product.get_by_product_and_supplier(db, product_id=product.id, supplier_id=supplier.id)
    assert sp is not None
    assert sp.lead_time_days == 10 # 10 days diff
