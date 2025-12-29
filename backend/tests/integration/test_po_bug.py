import pytest
from datetime import date
from src.crud.crud_purchase_order import purchase_order as crud_po
from src.crud.crud_supplier_product import supplier_product as crud_sp
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderItemCreate, PurchaseOrderUpdate
from src.schemas.product import ProductCreate
from src.schemas.supplier import SupplierCreate
from src.crud.crud_product import product as crud_product
from src.crud.crud_supplier import supplier as crud_supplier

@pytest.mark.db
def test_reproduce_missing_supplier_product(db):
    # 1. Setup Data
    supplier = crud_supplier.create(db, obj_in=SupplierCreate(name="Bug Test Supplier"))
    product = crud_product.create(db, obj_in=ProductCreate(name="Bug Test Product", sku="BUG-001", cost_price=10.0))
    
    # 2. Create PO
    po = crud_po.create_with_items(db, obj_in=PurchaseOrderCreate(
        supplier_id=supplier.id,
        ordered_at=date.today(),
        currency="USD",
        items=[PurchaseOrderItemCreate(product_id=product.id, quantity_ordered=10, unit_cost=10.0)]
    ))
    
    db.commit() # Commit creation
    
    # 3. Simulate new request - fetch PO fresh
    po_fresh = crud_po.get(db, id=po.id)
    
    # Receive PO (Complete it)
    # This should trigger _update_supplier_products
    crud_po.update(db, db_obj=po_fresh, obj_in=PurchaseOrderUpdate(
        status="completed",
        received_at=date.today()
    ))
    
    # 4. Verify SupplierProduct creation
    sp_list = crud_sp.get_by_product(db, product_id=product.id)
    
    assert len(sp_list) > 0, "SupplierProduct was not created upon PO completion!"
    sp = sp_list[0]
    assert sp.supplier_id == supplier.id
    assert sp.cost_price == 10.0
