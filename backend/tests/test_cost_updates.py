import pytest
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.crud.crud_product import product as crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderStatus
from src.schemas.product import ProductCreate
from src.schemas.supplier import SupplierCreate
from src.services.purchase_order_service import purchase_order_service

@pytest.mark.db
def test_cost_updates_on_receive(db, test_admin_user):
    # 1. Setup: Supplier & Product
    supplier = crud_supplier.create(db=db, obj_in=SupplierCreate(name="Cost Supplier"))
    
    # Initial Product: Clean slate, no cost
    product = crud_product.create(db=db, obj_in=ProductCreate(
        name="Cost Test Product", 
        sku="COST-101", 
        cost_price=0.0,
        default_resale_price=100.0
    ))
    
    assert product.average_cost == 0.0 or product.average_cost is None
    
    # 2. PO 1: Buy 10 units @ $10.00
    # Note: CRUD create expects schemas, but sqlalchemy relationship expects objects or dicts if simpler.
    # However, PurchaseOrderCreate schema defines items as PurchaseOrderItemCreate.
    # But CRUD base creates model from schema dump.
    # The issue is that generic CRUDBase doesn't handle nested creation automatically unless overridden or Pydantic handles it.
    # Let's use the explicit creation method found in other tests or crud_purchase_order.
    
    # Actually, simpler: just create PO then create Item manually or use a helper if available.
    # Checking crud_purchase_order.create... it overrides create to handle items?
    # No, earlier view showed it didn't override create. 
    # Let's create PO then Item.
    
    po1 = crud_purchase_order.create(db=db, obj_in=PurchaseOrderCreate(
        supplier_id=supplier.id,
        items=[] 
    ))
    
    # Manually add item
    from src.models.purchase_order_item import PurchaseOrderItem
    item1 = PurchaseOrderItem(
        po_id=po1.id,
        product_id=product.id,
        quantity_ordered=10,
        unit_cost=10.0
    )
    db.add(item1)
    db.commit()
    db.refresh(po1)
    
    # Transition to Ordered
    purchase_order_service.transition_status(
        db=db, po_id=po1.id, new_status=PurchaseOrderStatus.ORDERED
    )
    
    # Receive PO 1
    # Note: Using service directly to test logic
    purchase_order_service.receive_items(
        db=db, 
        po_id=po1.id, 
        received_items=[{"product_id": product.id, "quantity": 10}],
        user=test_admin_user
    )
    
    db.refresh(product)
    
    # Expect:
    # cost_price (LPP) = 10.0
    # average_cost = 10.0 ( (0*0 + 10*10) / 10 )
    assert product.cost_price == 10.0
    assert product.average_cost == 10.0
    
    # 3. PO 2: Buy 10 units @ $20.00
    po2 = crud_purchase_order.create(db=db, obj_in=PurchaseOrderCreate(
        supplier_id=supplier.id,
        items=[]
    ))
    item2 = PurchaseOrderItem(
        po_id=po2.id,
        product_id=product.id,
        quantity_ordered=10,
        unit_cost=20.0
    )
    db.add(item2)
    db.commit()
    db.refresh(po2)
    
    # Transition to Ordered
    purchase_order_service.transition_status(
        db=db, po_id=po2.id, new_status=PurchaseOrderStatus.ORDERED
    )
    
    # Receive PO 2
    purchase_order_service.receive_items(
        db=db, 
        po_id=po2.id, 
        received_items=[{"product_id": product.id, "quantity": 10}],
        user=test_admin_user
    )
    
    db.refresh(product)
    
    # Expect:
    # cost_price (LPP) = 20.0 (Updated to latest)
    # average_cost = 15.0 ( (10*10 + 10*20) / 20 ) -> (100 + 200) / 20 = 300 / 20 = 15
    assert product.cost_price == 20.0
    assert product.average_cost == 15.0
