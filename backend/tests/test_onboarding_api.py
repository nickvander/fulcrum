import pytest

from src.models.inventory import InventoryAdjustment
from src.models.product import Product
from src.models.purchase_order import PurchaseOrder
from src.models.store_settings import StoreSettings
from src.models.supplier import Supplier
from src.models.supplier_product import SupplierProduct


pytestmark = pytest.mark.db


def test_onboarding_status_reports_missing_setup(client):
    response = client.get("/api/v1/onboarding/status")

    assert response.status_code == 200
    data = response.json()
    steps = {step["key"]: step for step in data["steps"]}
    assert data["total_required"] == 7
    assert "products" in steps
    assert "suppliers" in steps
    assert "inventory" in steps
    assert steps["marketplaces"]["optional"] is True
    assert steps["marketplaces"]["warning"] is False


def test_onboarding_status_reports_core_setup(client, db):
    supplier = Supplier(name="Onboarding Supplier", currency="USD")
    product = Product(name="Onboarding Product", sku="ONBOARD-1")
    db.add_all([StoreSettings(store_name="Demo Store"), supplier, product])
    db.commit()
    db.refresh(supplier)
    db.refresh(product)

    db.add(
        SupplierProduct(
            supplier_id=supplier.id,
            product_id=product.id,
            supplier_product_name="Supplier Onboarding Product",
            cost_price=10,
        )
    )
    db.add(PurchaseOrder(supplier_id=supplier.id, status="ordered", currency="USD"))
    db.add(
        InventoryAdjustment(
            product_id=product.id,
            adjustment=1,
            reason="Onboarding stock",
            created_by="test",
        )
    )
    db.commit()

    response = client.get("/api/v1/onboarding/status")

    assert response.status_code == 200
    steps = {step["key"]: step for step in response.json()["steps"]}
    assert steps["store"]["complete"] is True
    assert steps["products"]["complete"] is True
    assert steps["suppliers"]["complete"] is True
    assert steps["supplier_matching"]["complete"] is True
    assert steps["purchase_orders"]["complete"] is True
    assert steps["inventory"]["complete"] is True
