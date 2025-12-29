import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.crud import crud_product
from src.schemas.product import ProductCreate

@pytest.mark.integration
def test_assemble_bundle(client: TestClient, db: Session, admin_headers):
    # 1. Create component
    comp_data = ProductCreate(
        name="Component A",
        sku="COMP-A",
        default_resale_price=10.0,
        cost_price=5.0,
        is_bundle=False
    )
    comp = crud_product.product.create(db, obj_in=comp_data)
    
    # 2. Add stock for component
    from src.services.inventory_service import inventory_service
    inventory_service.adjust_stock(db, comp.id, 100, location="default")
    db.commit()

    # 3. Create bundle
    bundle_data = ProductCreate(
        name="Bundle X",
        sku="BUNDLE-X",
        default_resale_price=20.0,
        cost_price=10.0,
        is_bundle=True,
        bundle_components=[]
    )
    bundle = crud_product.product.create(db, obj_in=bundle_data)
    
    # Add component to bundle
    from src.models.product import BundleComponent
    bc = BundleComponent(bundle_id=bundle.id, component_id=comp.id, quantity=2)
    db.add(bc)
    db.commit()
    db.refresh(bundle)

    # 4. Assemble 10 bundles
    # Consumes 20 components
    response = client.post(
        f"/api/v1/products/{bundle.id}/assemble",
        headers=admin_headers,
        json={"quantity": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bundle.id
    
    # Check bundle stock
    # Note: inventory_items might need refresh or be loaded
    # The response should include it if eager loaded
    inv_qty = 0
    if data.get("inventory_items"):
        inv_qty = data["inventory_items"][0]["quantity"]
    assert inv_qty == 10
    
    # Check component stock (need to fetch component again)
    db.refresh(comp)
    # Eager load inventory for component check would be better via API or DB query
    # But db.refresh should do clean check if mapped correctly, 
    # though inventory_items is a relationship.
    from src.models.inventory import InventoryItem
    comp_stock = db.query(InventoryItem).filter(InventoryItem.product_id == comp.id).first()
    assert comp_stock.quantity == 80

@pytest.mark.integration
def test_assemble_bundle_insufficient_stock(client: TestClient, db: Session, admin_headers):
    # Setup similar to above but with low stock
    comp_data = ProductCreate(name="Component Low", sku="COMP-LOW", default_resale_price=10.0, cost_price=5.0)
    comp = crud_product.product.create(db, obj_in=comp_data)
    
    from src.services.inventory_service import inventory_service
    inventory_service.adjust_stock(db, comp.id, 5, location="default") # Only 5 available
    db.commit()

    bundle_data = ProductCreate(name="Bundle Y", sku="BUNDLE-Y", default_resale_price=20.0, cost_price=10.0, is_bundle=True)
    bundle = crud_product.product.create(db, obj_in=bundle_data)
    
    from src.models.product import BundleComponent
    bc = BundleComponent(bundle_id=bundle.id, component_id=comp.id, quantity=1)
    db.add(bc)
    db.commit()

    # Try to assemble 10 (needs 10 comp)
    response = client.post(
        f"/api/v1/products/{bundle.id}/assemble",
        headers=admin_headers,
        json={"quantity": 10},
    )
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]
