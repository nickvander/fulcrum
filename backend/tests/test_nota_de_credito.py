"""Returns Phase 3 — nota de crédito (CFDI egreso) issuance (FP-06 P2).

Covers the credit-note path end to end against the deterministic mock PAC:
  * issue an egreso for a refund, linked to the original ingreso UUID
  * idempotency (a refund retry → ONE credit note)
  * skip when the order was never invoiced / is marketplace-handled
  * the credited amount is capped at the invoice total (across partials)
  * the POST endpoint (write-scoped) + read-only-key rejection
  * the mock provider's egreso is deterministic and distinct from the ingreso
"""
from __future__ import annotations

import hashlib

import pytest
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.api_key import ApiKey
from src.models.cfdi_document import CfdiDocument
from src.models.inventory import InventoryItem
from src.schemas.cfdi import CfdiIssuerConfigUpdate
from src.schemas.product import ProductCreate
from src.services import cfdi_service, cfdi_stamp_service
from src.services.invoicing import MockInvoicingProvider

pytestmark = pytest.mark.db

_BASE = "/api/v1/sales-orders"


def _configure_issuer(db: Session) -> None:
    cfdi_service.save_issuer_config(
        db,
        CfdiIssuerConfigUpdate(
            rfc="AAA010101AAA", name="Mi Tienda SA de CV", tax_regime="601", postal_code="06000"
        ),
    )


def _invoiced_order(db, client, admin_headers, *, sku, idem, price=116.0, qty=1) -> int:
    """Create an order WITH a receptor RFC so it auto-stamps an ingreso; return id."""
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name=f"NC {sku}", sku=sku, default_resale_price=price, cost_price=1.0),
    )
    db.add(InventoryItem(product_id=product.id, quantity=qty, location="default"))
    db.commit()
    resp = client.post(
        f"{_BASE}/",
        headers=admin_headers,
        json={
            "idempotency_key": idem,
            "items": [{"product_id": product.id, "quantity": qty}],
            "cfdi_receiver_rfc": "XAXX010101000",
            "cfdi_receiver_name": "Cliente Demo",
        },
    )
    assert resp.status_code == 201, resp.text
    order_id = resp.json()["id"]
    # Sanity: the ingreso stamped.
    ingreso = cfdi_stamp_service._existing_stamped(db, order_id)
    assert ingreso is not None and ingreso.uuid
    return order_id


def _api_key(db, user, raw_key: str, *, scope: str = "full") -> dict:
    db.add(
        ApiKey(
            user_id=user.id,
            name="nc key",
            key_prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            is_active=True,
            scope=scope,
        )
    )
    db.flush()
    return {"X-API-Key": raw_key}


# ---- service: issue_nota_de_credito ----------------------------------------- #


def test_issue_egreso_linked_to_original(client, db, admin_headers):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NC1", idem="nc-1")
    ingreso = cfdi_stamp_service._existing_stamped(db, order_id)

    out = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 11600, "ref-nc-1")
    doc = out["document"]
    assert doc.kind == "egreso"
    assert doc.status == "stamped"
    assert doc.related_uuid == ingreso.uuid  # linked to the original ingreso
    assert doc.uuid and doc.uuid != ingreso.uuid
    assert doc.total_cents == 11600
    assert doc.subtotal_cents + doc.iva_cents == 11600  # IVA backed out, sums back


def test_issue_is_idempotent(client, db, admin_headers):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NC2", idem="nc-2")

    first = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 5000, "ref-nc-2")
    second = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 5000, "ref-nc-2")
    assert first["document"].id == second["document"].id  # same row, no second stamp
    egresos = db.query(CfdiDocument).filter_by(order_id=order_id, kind="egreso").all()
    assert len(egresos) == 1


def test_no_ingreso_returns_skip(client, db, admin_headers):
    # An order with no stamped ingreso (created without a receptor → no autostamp).
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name="NoInv", sku="NOINV1", default_resale_price=50.0, cost_price=1.0),
    )
    db.add(InventoryItem(product_id=product.id, quantity=3, location="default"))
    db.commit()
    resp = client.post(
        f"{_BASE}/",
        headers=admin_headers,
        json={"idempotency_key": "noinv-1", "items": [{"product_id": product.id, "quantity": 1}]},
    )
    order_id = resp.json()["id"]
    out = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 5000, "ref-noinv")
    assert out == {"error": "no_ingreso"}


def test_amount_exceeds_invoice(client, db, admin_headers):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NC3", idem="nc-3")  # total 11600
    out = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 12000, "ref-nc-3")
    assert out["error"] == "amount_exceeds_invoice"
    assert out["creditable_cents"] == 11600


def test_partial_credits_capped_at_invoice_total(client, db, admin_headers):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NC4", idem="nc-4")  # total 11600
    a = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 8000, "ref-nc-4a")
    b = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 3600, "ref-nc-4b")
    assert "document" in a and "document" in b  # 8000 + 3600 == 11600, both fit
    # A third credit now exceeds the remaining (0).
    c = cfdi_stamp_service.issue_nota_de_credito(db, order_id, 100, "ref-nc-4c")
    assert c["error"] == "amount_exceeds_invoice"
    assert c["creditable_cents"] == 0


def test_invalid_amount(client, db, admin_headers):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NC5", idem="nc-5")
    assert cfdi_stamp_service.issue_nota_de_credito(db, order_id, 0, "ref-nc-5")["error"] == (
        "invalid_amount"
    )


# ---- endpoint --------------------------------------------------------------- #


def test_endpoint_issues_and_links(client, db, admin_headers, test_admin_user):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NCE1", idem="nce-1")
    ingreso = cfdi_stamp_service._existing_stamped(db, order_id)
    headers = _api_key(db, test_admin_user, "ncfull00-" + "a" * 55)

    resp = client.post(
        f"{_BASE}/{order_id}/nota-de-credito",
        headers=headers,
        json={"amount_cents": 11600, "idempotency_key": "ep-nc-1", "reason": "devolución"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["issued"] is True
    assert body["status"] == "stamped"
    assert body["related_uuid"] == ingreso.uuid
    assert body["amount_cents"] == 11600


def test_endpoint_skips_uninvoiced_order(client, db, admin_headers, test_admin_user):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(name="EpNoInv", sku="EPNOINV", default_resale_price=50.0, cost_price=1.0),
    )
    db.add(InventoryItem(product_id=product.id, quantity=3, location="default"))
    db.commit()
    resp = client.post(
        f"{_BASE}/",
        headers=admin_headers,
        json={"idempotency_key": "ep-noinv", "items": [{"product_id": product.id, "quantity": 1}]},
    )
    order_id = resp.json()["id"]
    headers = _api_key(db, test_admin_user, "ncfull01-" + "b" * 55)

    resp = client.post(
        f"{_BASE}/{order_id}/nota-de-credito",
        headers=headers,
        json={"amount_cents": 5000, "idempotency_key": "ep-noinv-nc"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "issued": False,
        "status": "no_ingreso",
        "uuid": None,
        "related_uuid": None,
        "amount_cents": 0,
    }


def test_endpoint_read_only_key_rejected(client, db, admin_headers, test_admin_user):
    _configure_issuer(db)
    order_id = _invoiced_order(db, client, admin_headers, sku="NCRO", idem="ncro-1")
    headers = _api_key(db, test_admin_user, "ncread00-" + "c" * 55, scope="read_only")

    resp = client.post(
        f"{_BASE}/{order_id}/nota-de-credito",
        headers=headers,
        json={"amount_cents": 11600, "idempotency_key": "ep-ro-nc"},
    )
    assert resp.status_code == 403, resp.text


# ---- mock provider ---------------------------------------------------------- #


def test_mock_egreso_is_deterministic_and_distinct():
    p = MockInvoicingProvider()
    r1 = p.nota_de_credito("ORIG-UUID-1", 11600)
    r2 = p.nota_de_credito("ORIG-UUID-1", 11600)
    assert r1.uuid == r2.uuid  # deterministic
    assert r1.uuid != "ORIG-UUID-1"  # distinct from the ingreso
    assert 'TipoDeComprobante="E"' in r1.xml
    assert "ORIG-UUID-1" in r1.xml  # CfdiRelacionado points at the original
