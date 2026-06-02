"""Tests for FP-06 P1 — CFDI live stamping (mock PAC).

Covers the per-channel invoicing policy (ML linked vs storefront stamped),
the stamp happy path + idempotency, issuer-not-configured guard, the
link-external path, and the HTTP contract.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.cfdi_document import CfdiDocument
from src.models.order import SalesOrder, SalesOrderItem
from src.schemas.cfdi import CfdiIssuerConfigUpdate
from src.schemas.product import ProductCreate
from src.services import cfdi_service, cfdi_stamp_service
from src.services.invoicing import MockInvoicingProvider


pytestmark = pytest.mark.db


def _configure_issuer(db):
    cfdi_service.save_issuer_config(db, CfdiIssuerConfigUpdate(
        rfc="AAA010101AAA", name="Mi Tienda SA de CV", tax_regime="601",
        postal_code="06000",
    ))


def _order(db, *, sku, source, qty=1, unit_price=116.0, status="COMPLETED"):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Stamp {sku}", sku=sku,
            default_resale_price=unit_price, cost_price=unit_price / 2,
        ),
    )
    order = SalesOrder(
        status=status, total_price=unit_price * qty, currency="MXN",
        created_at=datetime.utcnow(), source=source, external_order_id=f"EXT-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=unit_price, cost_per_unit=unit_price / 2,
    ))
    db.commit()
    return order


def test_policy_defaults(db):
    # ML stamps its own; storefront + Amazon are self-stamped by Fulcrum.
    assert cfdi_stamp_service.resolve_invoicing_source(db, "MERCADOLIBRE") == "marketplace_handled"
    assert cfdi_stamp_service.resolve_invoicing_source(db, "AMAZON") == "self"
    assert cfdi_stamp_service.resolve_invoicing_source(db, "FULCRUM") == "self"


def test_policy_override(db):
    cfdi_service.save_issuer_config(db, CfdiIssuerConfigUpdate(
        invoicing_policy={"MERCADOLIBRE": "self"},
    ))
    assert cfdi_stamp_service.resolve_invoicing_source(db, "MERCADOLIBRE") == "self"


def test_stamp_self_channel_happy_path(db):
    _configure_issuer(db)
    order = _order(db, sku="SELF", source="FULCRUM", qty=1, unit_price=116.0)

    result = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())

    doc = result["document"]
    assert doc.status == "stamped"
    assert doc.invoicing_source == "self"
    assert doc.uuid
    # 116 inclusive @16% -> 100 base + 16 IVA, in centavos, total consistent.
    assert doc.subtotal_cents == 10000
    assert doc.iva_cents == 1600
    assert doc.total_cents == doc.subtotal_cents + doc.iva_cents


def test_stamp_is_idempotent(db):
    _configure_issuer(db)
    order = _order(db, sku="IDEM", source="AMAZON", unit_price=116.0)

    first = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())
    second = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())

    assert first["document"].id == second["document"].id
    assert db.query(CfdiDocument).filter(CfdiDocument.order_id == order.id).count() == 1


def test_stamp_refuses_marketplace_handled(db):
    _configure_issuer(db)
    order = _order(db, sku="MLORD", source="MERCADOLIBRE", unit_price=116.0)

    result = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())

    assert result == {"error": "marketplace_handled"}
    assert db.query(CfdiDocument).filter(CfdiDocument.order_id == order.id).count() == 0


def test_stamp_requires_issuer_configured(db):
    # No issuer config saved in this fresh db.
    order = _order(db, sku="NOISS", source="FULCRUM", unit_price=116.0)
    result = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())
    assert result == {"error": "issuer_not_configured"}


def test_stamp_specific_receiver_rfc(db):
    _configure_issuer(db)
    order = _order(db, sku="RFC", source="FULCRUM", unit_price=116.0)
    order.cfdi_receiver_rfc = "XAXX010101000"
    order.cfdi_receiver_name = "Cliente Especifico"
    db.commit()

    result = cfdi_stamp_service.stamp_order(db, order.id, provider=MockInvoicingProvider())

    assert result["document"].receiver_rfc == "XAXX010101000"
    assert result["document"].receiver_name == "Cliente Especifico"


def test_link_external_records_ml_uuid(db):
    order = _order(db, sku="LINK", source="MERCADOLIBRE", unit_price=116.0)

    result = cfdi_stamp_service.link_external(
        db, order.id, "11111111-2222-3333-4444-555555555555", receiver_rfc="XAXX010101000",
    )

    doc = result["document"]
    assert doc.invoicing_source == "marketplace_handled"
    assert doc.uuid == "11111111-2222-3333-4444-555555555555"
    # Idempotent on the UUID.
    again = cfdi_stamp_service.link_external(db, order.id, "11111111-2222-3333-4444-555555555555")
    assert again["document"].id == doc.id


def test_unknown_order(db):
    assert cfdi_stamp_service.stamp_order(db, 999999, provider=MockInvoicingProvider()) == {"error": "not_found"}
    assert cfdi_stamp_service.link_external(db, 999999, "u") == {"error": "not_found"}


def test_stamp_endpoint_contract(client: TestClient, db, admin_headers):
    _configure_issuer(db)
    order = _order(db, sku="API", source="FULCRUM", unit_price=116.0)

    resp = client.post(f"/api/v1/reports/cfdi/{order.id}/stamp", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "stamped"
    assert body["uuid"]

    # ML order -> 409 marketplace_handled.
    ml = _order(db, sku="APIML", source="MERCADOLIBRE", unit_price=116.0)
    resp_ml = client.post(f"/api/v1/reports/cfdi/{ml.id}/stamp", headers=admin_headers)
    assert resp_ml.status_code == 409


def test_endpoints_require_auth(client: TestClient):
    assert client.post("/api/v1/reports/cfdi/1/stamp").status_code == 401
    assert client.get("/api/v1/reports/cfdi/1/document").status_code == 401
