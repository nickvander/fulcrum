import pytest
from sqlalchemy.orm import Session
from src.crud.crud_supplier import supplier as crud_supplier
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.schemas.supplier import SupplierCreate
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderStatus, PurchaseOrderItemCreate
from src.models.product import Product

# Mark all tests as requiring database
pytestmark = pytest.mark.db

@pytest.fixture
def db_session_fixture(db: Session):
    # This fixture is just a type hint helper if 'db' is already provided by conftest
    return db

@pytest.mark.db
def test_create_and_get_po_with_items(db: Session):
    # 1. Create a Supplier
    supplier_in = SupplierCreate(name="PO Test Supplier", currency="USD")
    supplier = crud_supplier.create(db=db, obj_in=supplier_in)
    
    # 2. Create a Product
    # Directly using model for simplicity in this integration test
    product = Product(
        name="PO Test Product",
        sku="PO-TEST-SKU-001",
        default_resale_price=10.0,
        cost_price=5.0
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 3. Create PO with Items
    po_item_in = PurchaseOrderItemCreate(
        product_id=product.id,
        quantity_ordered=10,
        unit_cost=5.0
    )
    
    po_in = PurchaseOrderCreate(
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.DRAFT,
        items=[po_item_in]
    )
    
    po = crud_purchase_order.create_with_items(db=db, obj_in=po_in)
    
    # 4. Verify PO
    assert po.id is not None
    assert po.supplier_id == supplier.id
    assert po.status == PurchaseOrderStatus.DRAFT.value # Enum stored as value in DB usually or need check
    assert len(po.items) == 1
    assert po.items[0].product_id == product.id
    assert po.items[0].quantity_ordered == 10
    assert po.items[0].unit_cost == 5.0
    assert po.total_amount == 50.0  # 10 * 5.0
    
    # 5. Clean up (Optional if tests run in transaction rollback)
    # The 'db' fixture usually handles rollback in pytest-flask-sqlalchemy setups, 
    # but let's see how the project is set up.

def test_update_po_status(db: Session):
     # 1. Create a Supplier
    supplier_in = SupplierCreate(name="Status Test Supplier")
    supplier = crud_supplier.create(db=db, obj_in=supplier_in)
    
    # 2. Create PO
    po_in = PurchaseOrderCreate(supplier_id=supplier.id)
    po = crud_purchase_order.create_with_items(db=db, obj_in=po_in)
    
    assert po.status == PurchaseOrderStatus.DRAFT.value
    
    # 3. Update Status
    # Note: crud.update takes dict or schema
    crud_purchase_order.update(db=db, db_obj=po, obj_in={"status": PurchaseOrderStatus.ORDERED})
    
    db.refresh(po)
    assert po.status == PurchaseOrderStatus.ORDERED.value
