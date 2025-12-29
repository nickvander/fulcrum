import pytest
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.crud.crud_product import product as crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.schemas.purchase_order import PurchaseOrderCreate
from src.schemas.product import ProductCreate
from src.schemas.supplier import SupplierCreate
from src.services.purchase_order_service import purchase_order_service

@pytest.mark.db
def test_calculate_landed_costs(db):
    # Setup
    supplier = crud_supplier.create(db=db, obj_in=SupplierCreate(name="Landed Cost Supplier"))
    p1 = crud_product.create(db=db, obj_in=ProductCreate(name="P1", sku="P1", cost_price=10.0))
    p2 = crud_product.create(db=db, obj_in=ProductCreate(name="P2", sku="P2", cost_price=20.0))
    
    # Create PO with 2 items
    po = crud_purchase_order.create(db=db, obj_in=PurchaseOrderCreate(
        supplier_id=supplier.id,
        shipping_cost=30.0,
        tax_amount=10.0,
        other_costs=5.0
    ))
    
    from src.models.purchase_order_item import PurchaseOrderItem
    item1 = PurchaseOrderItem(po_id=po.id, product_id=p1.id, quantity_ordered=10, base_cost=10.0)
    item2 = PurchaseOrderItem(po_id=po.id, product_id=p2.id, quantity_ordered=5, base_cost=20.0)
    db.add(item1)
    db.add(item2)
    db.commit()
    
    # Calculate Landed Costs
    # Total subtotal = (10 * 10) + (5 * 20) = 100 + 100 = 200
    # Total extra costs = 30 + 10 + 5 = 45
    # Each item contributes 50% to subtotal.
    # Item 1 share (of 30) = 15. Per unit (10 units) = 1.5
    # Item 2 share (of 30) = 15. Per unit (5 units) = 3.0
    
    purchase_order_service.calculate_landed_costs(db, po.id)
    
    db.refresh(item1)
    db.refresh(item2)
    
    assert item1.shipping_allocated == 15.0 / 10 # 1.5
    assert item1.taxes_allocated == 5.0 / 10 # 0.5
    assert item1.other_allocated == 2.5 / 10 # 0.25
    assert item1.unit_cost == 10.0 + 1.5 + 0.5 + 0.25 # 12.25
    
    assert item2.shipping_allocated == 15.0 / 5 # 3.0
    assert item2.unit_cost == 20.0 + 3.0 + 1.0 + 0.5 # 24.5
