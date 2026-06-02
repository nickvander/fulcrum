"""Tests for the SAT/CFDI factura export (B7), export-only v1.

Covers IVA back-out from tax-inclusive prices, público-general receiver,
the issuer-configured flag, date-range + realized-status filtering, the
issuer config save/read round-trip, and the HTTP contract.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.order import SalesOrder, SalesOrderItem
from src.schemas.cfdi import CfdiIssuerConfigUpdate
from src.schemas.product import ProductCreate
from src.services import cfdi_service


pytestmark = pytest.mark.db


def _order(db, *, sku, qty, unit_price, status="COMPLETED", days_ago=1):
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"CFDI {sku}", sku=sku,
            default_resale_price=unit_price, cost_price=unit_price / 2,
        ),
    )
    order = SalesOrder(
        status=status, total_price=unit_price * qty, currency="MXN",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
        source="mercadolibre", external_order_id=f"ML-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=unit_price, cost_per_unit=unit_price / 2,
    ))
    db.commit()
    return order


def test_iva_backed_out_of_tax_inclusive_price(db):
    # 116 inclusive @ 16% -> base 100, IVA 16.
    order = _order(db, sku="IVA", qty=1, unit_price=116.0)

    report = cfdi_service.build_cfdi_report(db)

    row = next(r for r in report.rows if r.order_id == order.id)
    assert row.subtotal == 100.0
    assert row.iva_amount == 16.0
    assert row.total == 116.0
    assert row.concepts[0].unit_price == 100.0


def test_receiver_is_publico_general(db):
    order = _order(db, sku="PUB", qty=2, unit_price=58.0)

    report = cfdi_service.build_cfdi_report(db)

    row = next(r for r in report.rows if r.order_id == order.id)
    assert row.receiver_rfc == cfdi_service.RFC_GENERICO
    assert row.receiver_name == cfdi_service.RECEIVER_PUBLICO_GENERAL


def test_issuer_configured_flag_round_trip(db):
    before = cfdi_service.read_issuer_config(db)
    assert before.is_configured is False

    cfdi_service.save_issuer_config(db, CfdiIssuerConfigUpdate(
        rfc="AAA010101AAA", name="Mi Tienda SA de CV", tax_regime="601",
        postal_code="06000",
    ))
    after = cfdi_service.read_issuer_config(db)
    assert after.is_configured is True
    assert after.rfc == "AAA010101AAA"
    assert after.tax_regime == "601"
    # Defaults preserved.
    assert after.iva_rate == 0.16
    assert after.default_unit_key == "H87"


def test_custom_iva_rate_changes_backout(db):
    cfdi_service.save_issuer_config(db, CfdiIssuerConfigUpdate(iva_rate=0.0))
    order = _order(db, sku="ZERO", qty=1, unit_price=100.0)

    report = cfdi_service.build_cfdi_report(db)

    row = next(r for r in report.rows if r.order_id == order.id)
    assert row.subtotal == 100.0
    assert row.iva_amount == 0.0


def test_only_realized_orders_in_range(db):
    realized = _order(db, sku="REAL", qty=1, unit_price=116.0, days_ago=2)
    _order(db, sku="PENDING", qty=1, unit_price=116.0, status="PENDING", days_ago=2)
    _order(db, sku="OLD", qty=1, unit_price=116.0, days_ago=400)

    report = cfdi_service.build_cfdi_report(
        db, start_date=date.today() - timedelta(days=10), end_date=date.today(),
    )

    ids = {r.order_id for r in report.rows}
    assert realized.id in ids
    # Pending status + out-of-range order excluded.
    assert all(r.source != "PENDING" for r in report.rows)
    assert len(ids) == 1


def test_per_document_subtotal_plus_iva_equals_total(db):
    # Multiple concepts whose IVA back-out rounds — the document must stay
    # internally consistent (CFDI requires Total = SubTotal + taxes).
    order = _order(db, sku="RND", qty=3, unit_price=33.33)

    report = cfdi_service.build_cfdi_report(db)

    row = next(r for r in report.rows if r.order_id == order.id)
    assert round(row.subtotal + row.iva_amount, 2) == row.total
    # Grand totals stay consistent too.
    assert round(report.subtotal + report.iva_amount, 2) == report.total


def test_report_totals_sum_rows(db):
    _order(db, sku="T1", qty=1, unit_price=116.0)
    _order(db, sku="T2", qty=1, unit_price=232.0)

    report = cfdi_service.build_cfdi_report(db)

    assert report.order_count >= 2
    assert round(report.subtotal + report.iva_amount, 2) == round(report.total, 2)


def test_endpoint_contract(client: TestClient, db, admin_headers):
    order = _order(db, sku="API", qty=1, unit_price=116.0)

    resp = client.get("/api/v1/reports/cfdi", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "issuer" in body
    assert any(r["order_id"] == order.id for r in body["rows"])


def test_settings_cfdi_save_and_get(client: TestClient, db, admin_headers):
    save = client.post(
        "/api/v1/settings/cfdi",
        json={"rfc": "BBB020202BBB", "name": "Otra Tienda", "tax_regime": "626"},
        headers=admin_headers,
    )
    assert save.status_code == 200, save.text
    assert save.json()["is_configured"] is True

    get = client.get("/api/v1/settings/cfdi", headers=admin_headers)
    assert get.status_code == 200
    assert get.json()["rfc"] == "BBB020202BBB"


def test_endpoint_requires_auth(client: TestClient):
    assert client.get("/api/v1/reports/cfdi").status_code == 401
    assert client.get("/api/v1/settings/cfdi").status_code == 401
