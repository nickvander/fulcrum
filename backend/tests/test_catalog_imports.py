import pytest
from fastapi.testclient import TestClient

from src.crud.crud_supplier import supplier as crud_supplier
from src.models.catalog_import import CatalogImport
from src.models.product import Product
from src.models.supplier_product import SupplierProduct
from src.schemas.supplier import SupplierCreate
from src.services.catalog_ingestion_service import catalog_ingestion_service


pytestmark = pytest.mark.db


CSV_EN = b"""sku,name,description,price,cost,category,brand
WIDG-100,Stainless Widget,Heavy-duty widget for industrial use,29.99,12.50,Tools,Acme
WIDG-200,Brass Widget,Premium widget,49.00,18.00,Tools,Acme
"""


CSV_ES_SEMI = (
    "sku;nombre;precio;costo;marca\n"
    "MEX-001;Botella Térmica;199,90;75,50;HydroMX\n"
    "MEX-002;Taza Cerámica;89,00;25,00;HydroMX\n"
).encode("utf-8")


def test_csv_parser_handles_en_headers_and_dollar_values():
    data = catalog_ingestion_service.ingest(file_name="catalog.csv", content=CSV_EN)
    assert len(data.items) == 2
    assert data.items[0].sku == "WIDG-100"
    assert data.items[0].name == "Stainless Widget"
    assert data.items[0].default_resale_price == 29.99
    assert data.items[0].cost_price == 12.50
    assert data.items[0].brand == "Acme"
    assert data.items[0].selected is True
    assert data.warnings == []


def test_csv_parser_handles_spanish_headers_semicolons_and_decimal_comma():
    data = catalog_ingestion_service.ingest(file_name="catalog.csv", content=CSV_ES_SEMI)
    assert len(data.items) == 2
    assert data.items[0].name == "Botella Térmica"
    assert data.items[0].default_resale_price == 199.90
    assert data.items[0].cost_price == 75.50
    assert data.items[1].brand == "HydroMX"


def test_csv_parser_warns_when_name_column_missing():
    data = catalog_ingestion_service.ingest(
        file_name="bad.csv",
        content=b"sku,price\nABC-1,10.00\n",
    )
    assert data.items == []
    assert any("name" in w.lower() for w in data.warnings)


def test_csv_parser_rejects_unsupported_extension():
    data = catalog_ingestion_service.ingest(
        file_name="catalog.pdf",
        content=b"%PDF-1.4 ...",
    )
    assert data.items == []
    assert any(".pdf" in w for w in data.warnings)


def test_catalog_review_upload_creates_pending_review_with_extracted_items(
    client: TestClient,
    db,
    admin_headers,
):
    response = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["source"] == "csv"
    assert body["file_name"] == "catalog.csv"
    items = body["extracted_data"]["items"]
    assert len(items) == 2
    assert items[0]["sku"] == "WIDG-100"
    assert items[0]["default_resale_price"] == 29.99
    assert items[0]["selected"] is True

    listed = client.get("/api/v1/catalog-imports/reviews", headers=admin_headers)
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


def test_catalog_review_approval_creates_products_and_links_supplier(
    client: TestClient,
    db,
    admin_headers,
):
    supplier = crud_supplier.create(
        db=db,
        obj_in=SupplierCreate(name="Acme MX", currency="MXN"),
    )

    upload = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
        params={"supplier_id": supplier.id},
    )
    assert upload.status_code == 200, upload.text
    review = upload.json()
    items = review["extracted_data"]["items"]

    approve = client.post(
        f"/api/v1/catalog-imports/reviews/{review['id']}/approve",
        json={"supplier_id": supplier.id, "items": items},
        headers=admin_headers,
    )

    assert approve.status_code == 200, approve.text
    payload = approve.json()
    assert payload["import_review"]["status"] == "approved"
    assert payload["import_review"]["supplier_id"] == supplier.id
    assert len(payload["created_product_ids"]) == 2
    assert payload["skipped_count"] == 0

    products = (
        db.query(Product).filter(Product.sku.in_(["WIDG-100", "WIDG-200"])).all()
    )
    assert {p.sku for p in products} == {"WIDG-100", "WIDG-200"}
    assert all(p.name in {"Stainless Widget", "Brass Widget"} for p in products)

    links = (
        db.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == supplier.id)
        .filter(SupplierProduct.product_id.in_([p.id for p in products]))
        .all()
    )
    assert len(links) == 2


def test_catalog_review_approval_skips_duplicate_sku_without_failing(
    client: TestClient,
    db,
    admin_headers,
):
    # Seed one product whose SKU collides with a row in the CSV
    client.post(
        "/api/v1/products",
        json={"name": "Existing", "sku": "WIDG-100", "default_resale_price": 10.0},
        headers=admin_headers,
    )

    upload = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
    )
    review = upload.json()

    approve = client.post(
        f"/api/v1/catalog-imports/reviews/{review['id']}/approve",
        json={"items": review["extracted_data"]["items"]},
        headers=admin_headers,
    )

    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert len(body["created_product_ids"]) == 1  # WIDG-200
    assert body["skipped_count"] == 1
    assert any("WIDG-100" in reason for reason in body["skipped_reasons"])


def test_catalog_review_unselected_rows_are_not_created(
    client: TestClient,
    db,
    admin_headers,
):
    upload = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
    )
    items = upload.json()["extracted_data"]["items"]
    items[1]["selected"] = False
    review_id = upload.json()["id"]

    approve = client.post(
        f"/api/v1/catalog-imports/reviews/{review_id}/approve",
        json={"items": items},
        headers=admin_headers,
    )

    body = approve.json()
    assert len(body["created_product_ids"]) == 1
    assert db.query(Product).filter(Product.sku == "WIDG-200").first() is None


def test_catalog_review_can_be_rejected(client: TestClient, db, admin_headers):
    upload = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
    )
    review_id = upload.json()["id"]

    reject = client.post(
        f"/api/v1/catalog-imports/reviews/{review_id}/reject",
        headers=admin_headers,
    )

    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"
    assert (
        db.query(CatalogImport).filter(CatalogImport.id == review_id).first().status
        == "rejected"
    )


def test_catalog_review_rejects_empty_upload(client: TestClient, admin_headers):
    response = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("empty.csv", b"", "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "apiErrors.catalogImport.emptyFile"


def test_catalog_review_approval_requires_at_least_one_selection(
    client: TestClient,
    admin_headers,
):
    upload = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.csv", CSV_EN, "text/csv")},
        headers=admin_headers,
    )
    items = upload.json()["extracted_data"]["items"]
    for i in items:
        i["selected"] = False

    approve = client.post(
        f"/api/v1/catalog-imports/reviews/{upload.json()['id']}/approve",
        json={"items": items},
        headers=admin_headers,
    )
    assert approve.status_code == 400
    assert approve.json()["code"] == "apiErrors.catalogImport.nothingSelected"
