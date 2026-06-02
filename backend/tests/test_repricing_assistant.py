"""Tests for the margin-floor repricing assistant (B6).

Covers the floor math (default-rate fallback and settled-rate path),
status classification (loss / below_floor / infeasible / healthy-skip),
the suggested-price round-up, and the apply path (success, reauth,
not-found) plus the HTTP contract.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.crud import crud_product
from src.models.marketplace import (
    Marketplace,
    MarketplaceCredential,
    MarketplaceListing,
)
from src.models.order import (
    OrderCostBreakdown,
    OrderSource,
    SalesOrder,
    SalesOrderItem,
)
from src.schemas.product import ProductCreate
from src.services import repricing_service


pytestmark = pytest.mark.db


def _ml(db, *, fee_rate=0.16, shipping=0.0) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = fee_rate
    mp.default_shipping_cost = shipping
    db.commit()
    db.refresh(mp)
    return mp


def _listing(db, mp, *, sku, cost, price, ext="ML-EXT") -> MarketplaceListing:
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Reprice {sku}", sku=sku,
            default_resale_price=price, cost_price=cost,
        ),
    )
    listing = MarketplaceListing(
        product_id=product.id,
        marketplace_id=mp.id,
        external_listing_id=f"{ext}-{sku}",
        status="active",
        marketplace_price=price,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def _row_for(report, listing_id):
    return next((r for r in report.rows if r.listing_id == listing_id), None)


def test_below_cost_listing_flagged_as_loss(db):
    mp = _ml(db, fee_rate=0.16, shipping=0.0)
    listing = _listing(db, mp, sku="LOSS", cost=40.0, price=45.0)

    report = repricing_service.build_repricing_report(db, margin_floor_percent=0.10)

    row = _row_for(report, listing.id)
    assert row is not None
    # margin = (45 - 40 - 7.2) / 45 < 0 -> loss
    assert row.status == "loss"
    assert row.rate_source == "estimated"
    # p_floor = 40 / (1 - 0.16 - 0.10) = 54.05 -> rounded up to the cent
    assert row.suggested_price >= 54.05
    # the suggestion should clear the floor
    assert row.suggested_margin_percent >= 10.0


def test_healthy_listing_is_skipped(db):
    mp = _ml(db, fee_rate=0.10, shipping=0.0)
    # cost 20 at price 100 -> margin = (100 - 20 - 10)/100 = 70% >> floor
    listing = _listing(db, mp, sku="HEALTHY", cost=20.0, price=100.0)

    report = repricing_service.build_repricing_report(db, margin_floor_percent=0.10)

    assert _row_for(report, listing.id) is None


def test_infeasible_when_fee_plus_floor_exceeds_one(db):
    mp = _ml(db, fee_rate=0.95, shipping=0.0)
    listing = _listing(db, mp, sku="INF", cost=10.0, price=12.0)

    report = repricing_service.build_repricing_report(db, margin_floor_percent=0.10)

    row = _row_for(report, listing.id)
    assert row is not None
    assert row.status == "infeasible"
    assert row.suggested_price is None


def test_settled_rate_is_preferred_over_default(db):
    # Default says 16%, but settled finance data says ~30% effective take.
    mp = _ml(db, fee_rate=0.16, shipping=0.0)
    listing = _listing(db, mp, sku="SETTLED", cost=40.0, price=60.0)

    order = SalesOrder(
        status="COMPLETED", total_price=100.0, currency="MXN",
        created_at=datetime.utcnow(), source=OrderSource.MERCADOLIBRE.value,
        external_order_id="ML-SETTLE-1",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=listing.product_id,
        quantity=1, price_per_unit=100.0, cost_per_unit=40.0,
    ))
    db.add(OrderCostBreakdown(
        order_id=order.id, currency="MXN", revenue_amount=100.0,
        marketplace_fees_amount=25.0, ad_spend_amount=5.0, other_cost_amount=0.0,
        shipping_cost_amount=0.0, fees_source="settled",
        computed_at=datetime.utcnow(),
    ))
    db.commit()

    report = repricing_service.build_repricing_report(db, margin_floor_percent=0.10)

    row = _row_for(report, listing.id)
    assert row is not None
    assert row.rate_source == "settled"
    # 30% effective take, not the 16% default
    assert abs(row.effective_fee_rate - 0.30) < 0.001


def test_apply_price_reauth_short_circuits(db, test_admin_user):
    mp = _ml(db)
    listing = _listing(db, mp, sku="REAUTH", cost=40.0, price=45.0)
    db.add(MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=mp.id,
        needs_reauthorization=True,
    ))
    db.commit()

    result = repricing_service.apply_price(
        db, listing_id=listing.id, price=60.0, user_id=test_admin_user.id,
    )
    assert result == {"error": "needs_reauthorization"}


def test_apply_price_unknown_listing(db, test_admin_user):
    result = repricing_service.apply_price(
        db, listing_id=999999, price=60.0, user_id=test_admin_user.id,
    )
    assert result == {"error": "not_found"}


def test_apply_price_no_credentials(db, test_admin_user):
    mp = _ml(db)
    listing = _listing(db, mp, sku="NOCRED", cost=40.0, price=45.0)

    result = repricing_service.apply_price(
        db, listing_id=listing.id, price=60.0, user_id=test_admin_user.id,
    )
    assert result == {"error": "no_credentials"}


def test_apply_price_success(db, test_admin_user, monkeypatch):
    mp = _ml(db)
    listing = _listing(db, mp, sku="OK", cost=40.0, price=45.0)
    db.add(MarketplaceCredential(
        user_id=test_admin_user.id, marketplace_id=mp.id,
        needs_reauthorization=False,
    ))
    db.commit()

    from src.services import marketplace_service as ms_module

    class _FakeConnector:
        async def sync_price(self, external_id, price, access_token=None):
            return True

    monkeypatch.setattr(
        ms_module.marketplace_service, "get_connector",
        lambda name: _FakeConnector(),
    )

    async def _fake_retry(db_, cred_id, fn):
        return await fn("fake-token")

    monkeypatch.setattr(
        ms_module.marketplace_service, "call_with_401_retry", _fake_retry,
    )

    result = repricing_service.apply_price(
        db, listing_id=listing.id, price=60.0, user_id=test_admin_user.id,
    )
    assert "listing" in result
    db.refresh(listing)
    assert listing.marketplace_price == 60.0


def test_endpoint_contract(client: TestClient, db, admin_headers):
    mp = _ml(db, fee_rate=0.16, shipping=0.0)
    listing = _listing(db, mp, sku="API", cost=40.0, price=45.0)

    resp = client.get(
        "/api/v1/reports/repricing?margin_floor_percent=10", headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["margin_floor_percent"] == 10.0
    assert any(r["listing_id"] == listing.id for r in body["rows"])


def test_endpoint_requires_auth(client: TestClient):
    resp = client.get("/api/v1/reports/repricing")
    assert resp.status_code == 401
