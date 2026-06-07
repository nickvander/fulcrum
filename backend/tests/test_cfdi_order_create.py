"""FP-06 P2 — CFDI receptor captured at order-create + auto-stamp + XML retrieval.

Covers the storefront/BFF end-to-end path: the order-create payload carries the
buyer's CFDI receptor (RFC/name/CP/régimen/uso); the endpoint persists it on the
order and best-effort auto-stamps an ingreso CFDI; the stamped XML is retrievable
server-to-server. Stamping uses the deterministic mock PAC (no PAC_API_KEY).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.cfdi_document import CfdiDocument
from src.models.inventory import InventoryItem
from src.models.order import SalesOrder
from src.models.product import Product
from src.schemas.cfdi import CfdiIssuerConfigUpdate
from src.schemas.product import ProductCreate
from src.services import cfdi_service, cfdi_stamp_service

pytestmark = pytest.mark.db


def _configure_issuer(db: Session) -> None:
    cfdi_service.save_issuer_config(
        db,
        CfdiIssuerConfigUpdate(
            rfc="AAA010101AAA",
            name="Mi Tienda SA de CV",
            tax_regime="601",
            postal_code="06000",
        ),
    )


def _product_with_stock(db: Session, *, sku: str, price: float = 116.0, qty: int = 5) -> Product:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name=f"CFDI {sku}", sku=sku, default_resale_price=price, cost_price=price / 2),
    )
    db.add(InventoryItem(product_id=product.id, quantity=qty, location="default"))
    db.commit()
    return product


def test_order_create_persists_receptor(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIRECP1")

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-recp-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
            "cfdi_receiver_name": "Cliente Demo",
            "cfdi_receiver_postal_code": "01000",
            "cfdi_receiver_regime": "616",
            "cfdi_use": "S01",
        },
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).one()
    assert order.cfdi_receiver_rfc == "XAXX010101000"
    assert order.cfdi_receiver_name == "Cliente Demo"
    assert order.cfdi_receiver_postal_code == "01000"
    assert order.cfdi_receiver_regime == "616"
    assert order.cfdi_use == "S01"


def test_order_create_autostamps_when_rfc_present(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIAUTO1")

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-auto-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
            "cfdi_receiver_name": "Cliente Demo",
        },
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    doc = cfdi_stamp_service.latest_document(db, order_id)
    assert doc is not None
    assert doc.status == "stamped"
    assert doc.uuid
    assert doc.receiver_rfc == "XAXX010101000"


def test_order_create_no_rfc_does_not_autostamp(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDINOSTAMP1")

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-nostamp-1",
            "items": [{"product_id": product.id, "quantity": 1}],
        },
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]
    assert cfdi_stamp_service.latest_document(db, order_id) is None


def test_autostamp_failure_does_not_fail_order(client: TestClient, db: Session, admin_headers: dict):
    """No issuer configured ⇒ stamping returns an error, but the order still 201s
    (stamping is best-effort and must never fail a valid paid order)."""
    # deliberately do NOT configure the issuer
    product = _product_with_stock(db, sku="CFDIFAIL1")

    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-fail-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
        },
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]
    # No stamped doc (issuer_not_configured), but the order exists.
    doc = cfdi_stamp_service.latest_document(db, order_id)
    assert doc is None
    assert db.query(SalesOrder).filter(SalesOrder.id == order_id).one()


def test_order_create_idempotent_retry_single_stamp(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIIDEM1", qty=10)

    body = {
        "idempotency_key": "cfdi-idem-1",
        "items": [{"product_id": product.id, "quantity": 1}],
        "cfdi_receiver_rfc": "XAXX010101000",
    }
    r1 = client.post("/api/v1/sales-orders/", headers=admin_headers, json=body)
    r2 = client.post("/api/v1/sales-orders/", headers=admin_headers, json=body)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    order_id = r1.json()["id"]
    docs = db.query(CfdiDocument).filter_by(order_id=order_id).all()
    assert len(docs) == 1  # idempotent stamp — exactly one document


def test_cfdi_xml_retrieval(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIXML1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-xml-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
        },
    )
    order_id = resp.json()["id"]

    xml_resp = client.get(f"/api/v1/reports/cfdi/{order_id}/xml", headers=admin_headers)
    assert xml_resp.status_code == 200
    assert "application/xml" in xml_resp.headers["content-type"]
    assert "attachment" in xml_resp.headers.get("content-disposition", "")
    assert len(xml_resp.content) > 0


def test_cfdi_xml_retrieval_requires_auth(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIXMLAUTH1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-xmlauth-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
        },
    )
    order_id = resp.json()["id"]
    # No auth header → rejected (the XML carries the receptor RFC + legal name).
    unauth = client.get(f"/api/v1/reports/cfdi/{order_id}/xml")
    assert unauth.status_code in (401, 403)


def _api_key_headers(db: Session, user, raw_key: str) -> dict:
    import hashlib

    from src.models.api_key import ApiKey

    db.add(
        ApiKey(
            user_id=user.id,
            name="BFF cfdi key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


def test_cfdi_document_and_xml_accept_api_key(client: TestClient, db: Session, admin_headers, test_admin_user):
    """The storefront BFF reads CFDI status + XML server-to-server (X-API-Key),
    not just with a JWT (FP-06 P2 confirmation screen)."""
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIAPIKEY1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-apikey-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
        },
    )
    order_id = resp.json()["id"]
    key_headers = _api_key_headers(db, test_admin_user, "bffcfdi-" + "a" * 56)

    doc = client.get(f"/api/v1/reports/cfdi/{order_id}/document", headers=key_headers)
    assert doc.status_code == 200
    assert doc.json()["status"] == "stamped"

    xml = client.get(f"/api/v1/reports/cfdi/{order_id}/xml", headers=key_headers)
    assert xml.status_code == 200


def test_cfdi_xml_404_when_not_stamped(client: TestClient, db: Session, admin_headers: dict):
    product = _product_with_stock(db, sku="CFDIXMLNONE1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-xmlnone-1",
            "items": [{"product_id": product.id, "quantity": 1}],
        },
    )
    order_id = resp.json()["id"]
    missing = client.get(f"/api/v1/reports/cfdi/{order_id}/xml", headers=admin_headers)
    assert missing.status_code == 404


def test_cfdi_pdf_retrieval(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIPDF1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-pdf-1",
            "items": [{"product_id": product.id, "quantity": 2}],
            "cfdi_receiver_rfc": "XAXX010101000",
            "cfdi_receiver_name": "Cliente PDF",
        },
    )
    order_id = resp.json()["id"]

    pdf_resp = client.get(f"/api/v1/reports/cfdi/{order_id}/pdf", headers=admin_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content[:4] == b"%PDF"  # valid PDF magic bytes
    assert "attachment" in pdf_resp.headers.get("content-disposition", "")


def test_cfdi_pdf_requires_auth(client: TestClient, db: Session, admin_headers: dict):
    _configure_issuer(db)
    product = _product_with_stock(db, sku="CFDIPDFAUTH1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-pdfauth-1",
            "items": [{"product_id": product.id, "quantity": 1}],
            "cfdi_receiver_rfc": "XAXX010101000",
        },
    )
    order_id = resp.json()["id"]
    assert client.get(f"/api/v1/reports/cfdi/{order_id}/pdf").status_code in (401, 403)


def test_cfdi_pdf_404_when_not_stamped(client: TestClient, db: Session, admin_headers: dict):
    product = _product_with_stock(db, sku="CFDIPDFNONE1")
    resp = client.post(
        "/api/v1/sales-orders/",
        headers=admin_headers,
        json={
            "idempotency_key": "cfdi-pdfnone-1",
            "items": [{"product_id": product.id, "quantity": 1}],
        },
    )
    order_id = resp.json()["id"]
    assert client.get(f"/api/v1/reports/cfdi/{order_id}/pdf", headers=admin_headers).status_code == 404
