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


# --- AI / PDF gating ---------------------------------------------------------


def test_capabilities_reports_csv_only_when_ai_is_off(client: TestClient, admin_headers):
    resp = client.get("/api/v1/catalog-imports/capabilities", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["csv"] is True
    assert body["ai"] is False
    assert body["ai_enabled"] is False
    assert body["ai_configured"] is False
    assert set(body["accepted_extensions"]) == {"csv", "tsv", "txt"}


def test_pdf_upload_is_rejected_with_localized_code_when_ai_is_off(
    client: TestClient,
    admin_headers,
):
    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "apiErrors.catalogImport.aiRequiredForFileType"
    assert body["params"]["extension"] == ".pdf"


def test_capabilities_reports_ai_ready_when_enabled_and_keyed(
    client: TestClient,
    db,
    admin_headers,
):
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    from src.core.encryption import encryption_service

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = encryption_service.encrypt("fake-key-for-tests")
    db.add(settings)
    db.commit()

    resp = client.get("/api/v1/catalog-imports/capabilities", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai"] is True
    assert body["ai_enabled"] is True
    assert body["ai_configured"] is True
    assert {"pdf", "png", "jpg", "jpeg", "csv"}.issubset(set(body["accepted_extensions"]))


def test_pdf_upload_returns_502_on_ai_failure(
    client: TestClient,
    db,
    admin_headers,
    monkeypatch,
):
    """When AI is configured but the orchestrator returns an error, the
    endpoint surfaces it as a localized 502 rather than corrupting the queue.
    """
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    from src.core.encryption import encryption_service
    from src.services.adk import orchestrator as orchestrator_module

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = encryption_service.encrypt("fake-key-for-tests")
    db.add(settings)
    db.commit()

    async def fake_parse_catalog(self, content, mime_type):
        return {"error": "model unavailable"}

    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "parse_catalog", fake_parse_catalog
    )

    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 502
    assert resp.json()["code"] == "apiErrors.catalogImport.aiExtractionFailed"


def test_pdf_upload_creates_review_from_ai_result_when_ready(
    client: TestClient,
    db,
    admin_headers,
    monkeypatch,
):
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    from src.core.encryption import encryption_service
    from src.services.adk import orchestrator as orchestrator_module

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = encryption_service.encrypt("fake-key-for-tests")
    db.add(settings)
    db.commit()

    async def fake_parse_catalog(self, content, mime_type):
        return {
            "items": [
                {
                    "sku": "PDF-1",
                    "name": "Widget From PDF",
                    "description": "Parsed by AI",
                    "cost_price": 10.0,
                    "default_resale_price": 25.0,
                    "category": "Tools",
                    "brand": "Acme",
                    "supplier_sku": None,
                },
                {"name": "", "sku": "PDF-2"},  # name-less row should be dropped
            ],
            "confidence": 0.9,
        }

    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "parse_catalog", fake_parse_catalog
    )

    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "ai"
    items = body["extracted_data"]["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "PDF-1"
    assert items[0]["name"] == "Widget From PDF"


def test_ai_result_low_confidence_attaches_warning():
    from src.services.catalog_ingestion_service import catalog_ingestion_service

    parsed = catalog_ingestion_service.ingest_ai_result(
        {
            "items": [{"name": "Hazy product", "cost_price": "12.50"}],
            "confidence": 0.35,
        }
    )
    assert any("low" in w.lower() for w in parsed.warnings)
    assert parsed.items[0].name == "Hazy product"
    assert parsed.items[0].cost_price == 12.50


# --- Vendor auto-link from AI extraction ------------------------------------


def _seed_ai_ready(db):
    """Helper: enable AI in the dev settings so the endpoint accepts PDFs."""
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    from src.core.encryption import encryption_service

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = encryption_service.encrypt("fake-key-for-tests")
    db.add(settings)
    db.commit()


def test_pdf_upload_auto_links_supplier_when_vendor_name_matches(
    client: TestClient,
    db,
    admin_headers,
    monkeypatch,
):
    """AI extracts a vendor name. Endpoint fuzzy-matches it against an
    existing Supplier and sets review.supplier_id automatically; the response
    echoes both the detected vendor and the matched supplier name."""
    from src.services.adk import orchestrator as orchestrator_module

    _seed_ai_ready(db)
    supplier = crud_supplier.create(
        db=db, obj_in=SupplierCreate(name="Acme Tools de México", currency="MXN"),
    )

    async def fake_parse_catalog(self, content, mime_type):
        return {
            "vendor_name": "Acme Tools de México, S.A. de C.V.",
            "items": [{"name": "Widget From PDF", "cost_price": 10.0}],
            "confidence": 0.9,
        }

    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "parse_catalog", fake_parse_catalog
    )

    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["supplier_id"] == supplier.id
    assert body["detected_vendor_name"] == "Acme Tools de México, S.A. de C.V."
    assert body["auto_linked_supplier_name"] == "Acme Tools de México"
    assert any("Auto-linked" in w for w in body["warnings"])


def test_pdf_upload_warns_when_vendor_name_doesnt_match_any_supplier(
    client: TestClient,
    db,
    admin_headers,
    monkeypatch,
):
    """When the AI returns a vendor name with no fuzzy match, supplier_id
    stays null but the response surfaces the detected name + a warning so
    the user knows to pick one manually."""
    from src.services.adk import orchestrator as orchestrator_module

    _seed_ai_ready(db)
    # Seed an unrelated supplier so we know the match has a corpus
    crud_supplier.create(db=db, obj_in=SupplierCreate(name="HydroMX"))

    async def fake_parse_catalog(self, content, mime_type):
        return {
            "vendor_name": "Completely Unknown Distributor Co.",
            "items": [{"name": "Anonymous Widget"}],
        }

    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "parse_catalog", fake_parse_catalog
    )

    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["supplier_id"] is None
    assert body["detected_vendor_name"] == "Completely Unknown Distributor Co."
    assert body["auto_linked_supplier_name"] is None
    assert any("did not match" in w for w in body["warnings"])


def test_pdf_upload_does_not_override_explicit_supplier_id(
    client: TestClient,
    db,
    admin_headers,
    monkeypatch,
):
    """If the user already picked a supplier at upload time, the auto-link
    should NOT override their choice — even if the AI extracts a vendor
    that fuzzy-matches a different supplier."""
    from src.services.adk import orchestrator as orchestrator_module

    _seed_ai_ready(db)
    explicit = crud_supplier.create(db=db, obj_in=SupplierCreate(name="My Chosen Supplier"))
    crud_supplier.create(db=db, obj_in=SupplierCreate(name="Acme Tools"))

    async def fake_parse_catalog(self, content, mime_type):
        return {
            "vendor_name": "Acme Tools",
            "items": [{"name": "Acme Widget"}],
        }

    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "parse_catalog", fake_parse_catalog
    )

    resp = client.post(
        "/api/v1/catalog-imports/reviews",
        params={"supplier_id": explicit.id},
        files={"file": ("catalog.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["supplier_id"] == explicit.id
    # detected_vendor_name still surfaces for transparency
    assert body["detected_vendor_name"] == "Acme Tools"
    # but no auto-link warning since we respected the user's choice
    assert body["auto_linked_supplier_name"] is None
    assert not any("Auto-linked" in w for w in body["warnings"])
