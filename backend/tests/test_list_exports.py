"""CSV + PDF list exports for purchase orders, sales orders, expenses, and
the inventory-adjustment audit log. Each report uses the shared
`report_export` helpers; these tests focus on:

- the right rows make it into the CSV (filters, sort, etc.)
- snake_case CSV column headers stay stable (consumers may build pipelines)
- the PDF byte stream is a real PDF with the right filename
"""
import csv
import io
import re
from datetime import datetime, timedelta, date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud.crud_supplier import supplier as crud_supplier
from src.models.expense import Expense as ExpenseModel
from src.models.inventory import InventoryAdjustment
from src.models.order import OrderSource, SalesOrder
from src.models.product import Product
from src.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from src.models.purchase_order_item import PurchaseOrderItem
from src.schemas.supplier import SupplierCreate


# --- Purchase orders --------------------------------------------------------


@pytest.mark.db
def test_purchase_orders_csv_lists_each_po_with_supplier_and_totals(
    client: TestClient, admin_headers: dict, db: Session
):
    supplier = crud_supplier.create(
        db=db, obj_in=SupplierCreate(name="Acme Supply", currency="USD")
    )
    product = Product(name="Widget", sku="W-1", default_resale_price=10.0,
                      cost_price=4.0, is_bundle=False)
    db.add(product)
    db.flush()

    po = PurchaseOrder(
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.DRAFT,
        currency="USD",
        shipping_cost=5.0,
        tax_amount=2.0,
    )
    db.add(po)
    db.flush()
    db.add(PurchaseOrderItem(
        po_id=po.id, product_id=product.id, quantity_ordered=3, unit_cost=4.0,
    ))
    db.commit()

    response = client.get("/api/v1/purchase-orders/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-purchase-orders-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "po_id", "status", "supplier_name", "currency",
        "ordered_at", "received_at", "items_count",
        "subtotal", "shipping_cost", "tax_amount", "other_costs", "total_amount",
    ]
    body = rows[1]
    assert body[2] == "Acme Supply"
    assert body[6] == "1"                # items_count
    assert body[7] == "USD 12.00"        # subtotal (3 * 4)
    assert body[8] == "USD 5.00"         # shipping
    assert body[9] == "USD 2.00"         # tax
    assert body[11] == "USD 19.00"       # total (12 + 5 + 2 + 0)


@pytest.mark.db
def test_purchase_orders_csv_filters_by_status(
    client: TestClient, admin_headers: dict, db: Session
):
    supplier = crud_supplier.create(db=db, obj_in=SupplierCreate(name="Supp"))
    db.add_all([
        PurchaseOrder(supplier_id=supplier.id, status=PurchaseOrderStatus.DRAFT),
        PurchaseOrder(supplier_id=supplier.id, status=PurchaseOrderStatus.ORDERED),
    ])
    db.commit()

    resp = client.get(
        "/api/v1/purchase-orders/export",
        params={"status": "ORDERED"},  # API is forgiving on case
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert len(rows) == 2  # header + 1 row
    # The column emits the underlying enum value (lowercase), matching what
    # other endpoints return so consumers see one shape across the surface.
    assert rows[1][1] == "ordered"


@pytest.mark.db
def test_purchase_orders_pdf_renders_with_filename(
    client: TestClient, admin_headers: dict, db: Session
):
    response = client.get("/api/v1/purchase-orders/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    body = response.content
    assert body.startswith(b"%PDF-")
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-purchase-orders-\d{4}-\d{2}-\d{2}\.pdf"', cd)


# --- Sales orders -----------------------------------------------------------


@pytest.mark.db
def test_sales_orders_csv_lists_each_order_with_channel_label(
    client: TestClient, admin_headers: dict, db: Session
):
    db.add_all([
        SalesOrder(status="COMPLETED", total_price=99.50, created_at=datetime.utcnow(),
                   source=OrderSource.MERCADOLIBRE, external_order_id="ML-EXP-1"),
        SalesOrder(status="PENDING", total_price=42.00, created_at=datetime.utcnow(),
                   source=OrderSource.AMAZON, external_order_id="AMZ-EXP-1"),
    ])
    db.commit()

    response = client.get("/api/v1/sales-orders/export", headers=admin_headers)
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-sales-orders-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "order_id", "channel", "external_order_id", "status", "total_price", "created_at",
    ]
    body_by_ext = {r[2]: r for r in rows[1:]}
    assert body_by_ext["ML-EXP-1"][1] == "MercadoLibre"
    assert body_by_ext["ML-EXP-1"][4] == "USD 99.50"
    assert body_by_ext["AMZ-EXP-1"][1] == "Amazon"


@pytest.mark.db
def test_sales_orders_csv_filters_by_source(
    client: TestClient, admin_headers: dict, db: Session
):
    db.add_all([
        SalesOrder(status="COMPLETED", total_price=1.0, created_at=datetime.utcnow(),
                   source=OrderSource.MERCADOLIBRE, external_order_id="ML-FILTER-1"),
        SalesOrder(status="COMPLETED", total_price=2.0, created_at=datetime.utcnow(),
                   source=OrderSource.AMAZON, external_order_id="AMZ-FILTER-1"),
    ])
    db.commit()

    resp = client.get(
        "/api/v1/sales-orders/export",
        params={"source": "MERCADOLIBRE"},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert len(rows) == 2  # header + 1
    assert rows[1][1] == "MercadoLibre"


@pytest.mark.db
def test_sales_orders_pdf_renders(client: TestClient, admin_headers: dict, db: Session):
    response = client.get("/api/v1/sales-orders/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


# --- Expenses ---------------------------------------------------------------


@pytest.mark.db
def test_expenses_csv_lists_each_expense_with_amount_and_currency(
    client: TestClient, admin_headers: dict, db: Session
):
    db.add_all([
        ExpenseModel(description="AWS bill", amount=120.50, currency="USD",
                     category="Software", date=date.today(), expense_type="one_time"),
        ExpenseModel(description="Office rent", amount=2500.0, currency="MXN",
                     category="Rent", date=date.today(), expense_type="recurring"),
    ])
    db.commit()

    response = client.get("/api/v1/expenses/export", headers=admin_headers)
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert re.search(r'filename="fulcrum-expenses-\d{4}-\d{2}-\d{2}\.csv"', cd)

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "expense_id", "date", "description", "category",
        "amount", "currency", "expense_type", "payment_method",
        "reference_number", "paid_by", "is_reimbursed",
    ]
    body_by_desc = {r[2]: r for r in rows[1:]}
    assert body_by_desc["AWS bill"][4] == "USD 120.50"
    assert body_by_desc["AWS bill"][5] == "USD"
    assert body_by_desc["Office rent"][6] == "recurring"


@pytest.mark.db
def test_expenses_csv_filters_by_category(
    client: TestClient, admin_headers: dict, db: Session
):
    db.add_all([
        ExpenseModel(description="A", amount=1.0, currency="USD",
                     category="Software", date=date.today(), expense_type="one_time"),
        ExpenseModel(description="B", amount=1.0, currency="USD",
                     category="Marketing", date=date.today(), expense_type="one_time"),
    ])
    db.commit()

    resp = client.get(
        "/api/v1/expenses/export",
        params={"category": "Software"},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert len(rows) == 2  # header + 1
    assert rows[1][3] == "Software"


@pytest.mark.db
def test_expenses_pdf_renders(client: TestClient, admin_headers: dict, db: Session):
    response = client.get("/api/v1/expenses/export-pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


# --- Inventory adjustments --------------------------------------------------


@pytest.mark.db
def test_inventory_adjustments_csv_logs_who_what_when(
    client: TestClient, admin_headers: dict, db: Session
):
    product = Product(name="Audited Widget", sku="AUDIT-1",
                      default_resale_price=10.0, cost_price=4.0, is_bundle=False)
    db.add(product)
    db.flush()
    db.add_all([
        InventoryAdjustment(
            product_id=product.id, adjustment=+10,
            reason="Restock", timestamp=datetime.utcnow(),
            created_by="admin@example.com",
        ),
        InventoryAdjustment(
            product_id=product.id, adjustment=-2,
            reason="Damage write-off", timestamp=datetime.utcnow() - timedelta(hours=1),
            created_by="warehouse@example.com",
        ),
    ])
    db.commit()

    response = client.get(
        "/api/v1/reports/inventory-adjustments/export", headers=admin_headers,
    )
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    assert re.search(
        r'filename="fulcrum-inventory-adjustments-\d{4}-\d{2}-\d{2}\.csv"', cd
    )

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "timestamp", "product_id", "product_sku", "product_name",
        "adjustment", "reason", "created_by",
    ]
    # Newest first — +10 (Restock) before -2 (Damage write-off)
    assert rows[1][4] == "10"
    assert rows[1][5] == "Restock"
    assert rows[1][6] == "admin@example.com"
    assert rows[2][4] == "-2"
    assert rows[2][6] == "warehouse@example.com"


@pytest.mark.db
def test_inventory_adjustments_csv_filters_by_product(
    client: TestClient, admin_headers: dict, db: Session
):
    p1 = Product(name="P1", sku="P1-1", default_resale_price=10.0,
                 cost_price=4.0, is_bundle=False)
    p2 = Product(name="P2", sku="P2-1", default_resale_price=10.0,
                 cost_price=4.0, is_bundle=False)
    db.add_all([p1, p2])
    db.flush()
    db.add_all([
        InventoryAdjustment(product_id=p1.id, adjustment=+5,
                            reason="r1", created_by="u1"),
        InventoryAdjustment(product_id=p2.id, adjustment=+3,
                            reason="r2", created_by="u2"),
    ])
    db.commit()

    resp = client.get(
        "/api/v1/reports/inventory-adjustments/export",
        params={"product_id": p1.id},
        headers=admin_headers,
    )
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert len(rows) == 2  # header + 1
    assert rows[1][2] == "P1-1"
    assert rows[1][4] == "5"


@pytest.mark.db
def test_inventory_adjustments_pdf_renders(
    client: TestClient, admin_headers: dict, db: Session
):
    response = client.get(
        "/api/v1/reports/inventory-adjustments/export-pdf",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
