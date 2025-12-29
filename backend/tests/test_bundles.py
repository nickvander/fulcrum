import pytest
from src.crud.crud_product import product as crud_product
from src.schemas.product import ProductCreate

@pytest.mark.db
def test_create_bundle(db):
    # Create components
    c1 = crud_product.create(db, obj_in=ProductCreate(name="Comp 1", sku="C1", cost_price=5.0))
    c2 = crud_product.create(db, obj_in=ProductCreate(name="Comp 2", sku="C2", cost_price=10.0))
    
    # Create bundle
    bundle = crud_product.create(db, obj_in=ProductCreate(
        name="Bundle Box", 
        sku="B1", 
        is_bundle=True
    ))
    
    from src.models.product import BundleComponent
    bc1 = BundleComponent(bundle_id=bundle.id, component_id=c1.id, quantity=2)
    bc2 = BundleComponent(bundle_id=bundle.id, component_id=c2.id, quantity=1)
    db.add(bc1)
    db.add(bc2)
    db.commit()
    db.refresh(bundle)
    
    assert len(bundle.bundle_components) == 2
    # Verify quantities
    qty_map = {bc.component_id: bc.quantity for bc in bundle.bundle_components}
    assert qty_map[c1.id] == 2
    assert qty_map[c2.id] == 1
