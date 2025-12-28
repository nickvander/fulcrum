import pytest
from src.crud.crud_product import product as crud_product
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.crud.crud_supplier import supplier as crud_supplier
from src.schemas.product import ProductCreate
from src.schemas.supplier import SupplierCreate
from src.schemas.purchase_order import PurchaseOrderCreate
from src.models.purchase_order_item import PurchaseOrderItem

@pytest.mark.db
def test_product_purchase_history(db, client, test_admin_user):
    # 1. Setup
    supplier = crud_supplier.create(db=db, obj_in=SupplierCreate(name="History Supplier"))
    product = crud_product.create(db=db, obj_in=ProductCreate(name="History Product", sku="HIST-001", cost_price=0.0))
    
    # 2. Create POs (One received, one ordered)
    # PO 1: Received (Should show up)
    po1 = crud_purchase_order.create(db=db, obj_in=PurchaseOrderCreate(supplier_id=supplier.id, items=[]))
    item1 = PurchaseOrderItem(
        po_id=po1.id, product_id=product.id,
        quantity_ordered=10, unit_cost=5.0, quantity_received=10
    )
    db.add(item1)
    db.commit()
    
    # PO 2: Ordered (Should also show up)
    po2 = crud_purchase_order.create(db=db, obj_in=PurchaseOrderCreate(supplier_id=supplier.id, items=[]))
    item2 = PurchaseOrderItem(
        po_id=po2.id, product_id=product.id,
        quantity_ordered=20, unit_cost=6.0, quantity_received=0
    )
    db.add(item2)
    db.commit()
    
    # 3. Call Endpoint
    response = client.get(f"/api/v1/products/{product.id}/purchase-history")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    
    # Verify sorts (latest first usually, but POs created same time roughly. ID might differentiate or time)
    # My endpoint sorts by created_at desc.
    # po2 created after po1.
    assert data[0]["po_id"] == po2.id
    assert data[0]["quantity"] == 20.0
    assert data[0]["unit_cost"] == 6.0
    
    assert data[1]["po_id"] == po1.id
    assert data[1]["quantity"] == 10.0
    assert data[1]["unit_cost"] == 5.0
