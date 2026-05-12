import pytest

from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.product import Product
from src.models.purchase_order import PurchaseOrder
from src.models.purchase_order_item import PurchaseOrderItem
from src.models.store_settings import StoreSettings
from src.models.supplier import Supplier
from src.models.supplier_document_import import SupplierDocumentImport
from src.models.supplier_product import SupplierProduct
from src.models.supplier_product_alias import SupplierProductAlias


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


def test_demo_workspace_creates_customer_onboarding_records(client, db, admin_headers):
    response = client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert "purchase_order" in data["created_resources"]
    assert "inventory_receipt" in data["created_resources"]

    product = db.query(Product).filter(Product.sku == "DEMO-STARTER-WIDGET").one()
    supplier = db.query(Supplier).filter(Supplier.email == "demo-alibaba-supplier@fulcrum-demo.com").one()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == data["purchase_order_id"]).one()
    inventory = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()
    alias = (
        db.query(SupplierProductAlias)
        .filter(
            SupplierProductAlias.supplier_id == supplier.id,
            SupplierProductAlias.product_id == product.id,
        )
        .one()
    )

    assert po.status == "completed"
    assert po.items[0].quantity_received == 5
    assert inventory.quantity == 5
    assert product.average_cost == 12.5
    assert alias.alias_sku == "ALI-DEMO-WIDGET-001"
    assert alias.alias_name == "Alibaba Demo Starter Widget"

    status_response = client.get("/api/v1/onboarding/status")
    steps = {step["key"]: step for step in status_response.json()["steps"]}
    assert steps["store"]["complete"] is True
    assert steps["products"]["complete"] is True
    assert steps["suppliers"]["complete"] is True
    assert steps["supplier_matching"]["complete"] is True
    assert steps["purchase_orders"]["complete"] is True
    assert steps["inventory"]["complete"] is True


def test_demo_workspace_does_not_duplicate_stock(client, db, admin_headers):
    first_response = client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)
    second_response = client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["created"] is False

    product = db.query(Product).filter(Product.sku == "DEMO-STARTER-WIDGET").one()
    inventory = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).one()

    assert inventory.quantity == 5
    assert db.query(PurchaseOrder).filter(PurchaseOrder.notes.like("Fulcrum demo workspace%")).count() == 1


def test_demo_data_report_lists_cleanup_records(client, admin_headers):
    client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)

    response = client.get("/api/v1/onboarding/demo-data")

    assert response.status_code == 200
    report = response.json()
    assert report["has_demo_data"] is True
    assert report["cleanup_available"] is True
    record_types = {record["type"] for record in report["records"]}
    assert "Supplier" in record_types
    assert "Product" in record_types
    assert "Purchase order" in record_types
    assert "Inventory" in record_types

    readiness_response = client.get("/api/v1/onboarding/launch-readiness")
    sections = {section["key"]: section for section in readiness_response.json()["sections"]}
    assert sections["demo_data"]["status"] == "needs_attention"
    assert sections["demo_data"]["cleanup_available"] is True
    assert sections["demo_data"]["records"]


def test_demo_data_cleanup_removes_only_seeded_records(client, db, admin_headers):
    client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)

    response = client.post(
        "/api/v1/onboarding/demo-data/cleanup",
        headers=admin_headers,
        json={"confirm": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["cleaned"] is True
    assert result["has_demo_data"] is False
    assert "product and demo inventory" in result["removed_records"]
    assert db.query(Product).filter(Product.sku == "DEMO-STARTER-WIDGET").count() == 0
    assert (
        db.query(Supplier)
        .filter(Supplier.email == "demo-alibaba-supplier@fulcrum-demo.com")
        .count()
        == 0
    )
    assert db.query(PurchaseOrder).filter(PurchaseOrder.notes.like("Fulcrum demo workspace%")).count() == 0
    assert db.query(InventoryItem).count() == 0
    assert db.query(InventoryAdjustment).count() == 0
    assert db.query(SupplierProductAlias).count() == 0
    assert db.query(SupplierProduct).count() == 0


def test_demo_data_cleanup_blocks_when_demo_product_has_customer_links(client, db, admin_headers):
    client.post("/api/v1/onboarding/demo-workspace", headers=admin_headers)
    product = db.query(Product).filter(Product.sku == "DEMO-STARTER-WIDGET").one()
    supplier = db.query(Supplier).filter(Supplier.email == "demo-alibaba-supplier@fulcrum-demo.com").one()
    extra_po = PurchaseOrder(supplier_id=supplier.id, status="ordered", currency="USD")
    db.add(extra_po)
    db.commit()
    db.refresh(extra_po)
    db.add(
        PurchaseOrderItem(
            po_id=extra_po.id,
            product_id=product.id,
            quantity_ordered=1,
            unit_cost=99,
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/onboarding/demo-data/cleanup",
        headers=admin_headers,
        json={"confirm": True},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "non-demo purchase orders" in " ".join(detail["blocked_reasons"])
    assert db.query(Product).filter(Product.sku == "DEMO-STARTER-WIDGET").count() == 1


def test_launch_readiness_reports_pending_supplier_imports(client, db):
    supplier = Supplier(name="Readiness Supplier", currency="USD")
    product = Product(name="Readiness Product", sku="READY-1")
    db.add_all([StoreSettings(store_name="Ready Store"), supplier, product])
    db.commit()
    db.refresh(supplier)
    db.refresh(product)

    db.add(
        SupplierDocumentImport(
            file_name="alibaba-ready.pdf",
            content_type="application/pdf",
            status="pending",
            mode="create",
            extracted_data={"items": []},
            warnings=["Needs product match"],
        )
    )
    db.commit()

    response = client.get("/api/v1/onboarding/launch-readiness")

    assert response.status_code == 200
    report = response.json()
    sections = {section["key"]: section for section in report["sections"]}
    assert report["status"] in {"blocked", "needs_attention"}
    assert sections["supplier_documents"]["status"] == "needs_attention"
    assert sections["supplier_documents"]["metrics"]["pending_imports"] == 1
