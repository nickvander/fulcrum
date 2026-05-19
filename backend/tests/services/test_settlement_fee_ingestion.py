"""Coverage for `services/settlement_fee_ingestion.py` and the
connector settlement parsers.

Two layers:

  1. Pure connector parsers (`_extract_settlement_from_order`,
     `_extract_settlement_from_events`) — fixture JSON only, no
     network. Verifies the field-precedence rules + tolerance for
     ML's evolving payment shapes + Amazon's optional-vs-present
     field handling.
  2. End-to-end against a real DB session — order + breakdown is
     created with estimated fees, the sync flips it to settled, a
     subsequent cost-engine recompute preserves the settled values.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.marketplace import Marketplace, MarketplaceCredential
from src.models.order import (
    OrderSource,
    SalesOrder,
    SalesOrderItem,
)
from src.schemas.product import ProductCreate
from src.services import order_cost_engine
from src.services.marketplaces.amazon import AmazonConnector
from src.services.marketplaces.mercadolibre import MercadoLibreConnector
from src.services.settlement_fee_ingestion import (
    sync_settlement_for_credential,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# ML connector: _extract_settlement_from_order
# ---------------------------------------------------------------------------


def test_ml_extract_uses_fee_details_when_present():
    """Newer ML revision: fee_details[] is preferred over the legacy
    top-level marketplace_fee. Sum across all fee_details rows."""
    data = {
        "payments": [
            {
                "status": "approved",
                "marketplace_fee": 99.0,  # should be ignored when fee_details is present
                "fee_details": [
                    {"amount": 12.5, "type": "mercadopago_fee"},
                    {"amount": 7.5, "type": "marketplace_fee"},
                ],
            }
        ],
        "shipping": {"shipping_cost": 89.0},
    }
    result = MercadoLibreConnector._extract_settlement_from_order(data)
    assert result["marketplace_fees_amount"] == 20.0
    assert result["shipping_cost_amount"] == 89.0


def test_ml_extract_falls_back_to_legacy_marketplace_fee():
    """When fee_details is absent, the legacy `marketplace_fee` is summed."""
    data = {
        "payments": [
            {"status": "approved", "marketplace_fee": 15.0},
            {"status": "approved", "marketplace_fee": 5.5},
        ],
        "shipping": {"cost": 50.0},  # alternative shipping key
    }
    result = MercadoLibreConnector._extract_settlement_from_order(data)
    assert result["marketplace_fees_amount"] == 20.5
    assert result["shipping_cost_amount"] == 50.0


def test_ml_extract_skips_refunded_payments():
    """A refunded payment's fee residual is meaningless — skip it."""
    data = {
        "payments": [
            {"status": "approved", "marketplace_fee": 10.0},
            {"status": "refunded", "marketplace_fee": 999.0},
        ],
        "shipping": {},
    }
    result = MercadoLibreConnector._extract_settlement_from_order(data)
    assert result["marketplace_fees_amount"] == 10.0


def test_ml_extract_returns_none_when_no_fee_data_yet():
    """A pending order with no fee fields populated returns None on
    both keys → the worker leaves the row in estimated state."""
    data = {"payments": [{"status": "pending"}], "shipping": {}}
    result = MercadoLibreConnector._extract_settlement_from_order(data)
    assert result["marketplace_fees_amount"] is None
    assert result["shipping_cost_amount"] is None


def test_ml_extract_handles_missing_payments():
    """No payments key at all (older order, or refund-only stub) →
    both fields are None."""
    result = MercadoLibreConnector._extract_settlement_from_order({})
    assert result["marketplace_fees_amount"] is None
    assert result["shipping_cost_amount"] is None


# ---------------------------------------------------------------------------
# Amazon connector: _extract_settlement_from_events
# ---------------------------------------------------------------------------


def test_amazon_extract_sums_all_fee_types():
    """Commission + FBA fees + per-order fee should all roll into one
    `marketplace_fees_amount`. ShippingChargeList contributes to
    `shipping_cost_amount`."""
    events = {
        "ShipmentEventList": [
            {
                "ShipmentItemList": [
                    {
                        "ItemFeeList": [
                            {"FeeType": "Commission", "FeeAmount": {"Amount": "-15.00", "CurrencyCode": "MXN"}},
                            {"FeeType": "FBAPerOrderFulfillmentFee", "FeeAmount": {"Amount": "-3.50", "CurrencyCode": "MXN"}},
                        ],
                    },
                    {
                        "ItemFeeList": [
                            {"FeeType": "FBAWeightBasedFee", "FeeAmount": {"Amount": "-2.10", "CurrencyCode": "MXN"}},
                        ],
                    },
                ],
                "ShippingChargeList": [
                    {"ChargeType": "Shipping", "ChargeAmount": {"Amount": "12.00", "CurrencyCode": "MXN"}},
                ],
            }
        ]
    }
    result = AmazonConnector._extract_settlement_from_events(events)
    # Amazon reports fees as negative amounts (debit to seller). The
    # parser takes the absolute value so the cost engine sees a
    # positive cost component.
    assert result["marketplace_fees_amount"] == pytest.approx(20.60)
    assert result["shipping_cost_amount"] == pytest.approx(12.00)


def test_amazon_extract_returns_none_when_no_events():
    """Empty financial events payload → both fields None so the
    worker leaves the row in estimated state."""
    result = AmazonConnector._extract_settlement_from_events({})
    assert result["marketplace_fees_amount"] is None
    assert result["shipping_cost_amount"] is None


def test_amazon_extract_handles_refund_events():
    """Refund event list contributes both fees and shipping (with
    flipped signs in real SP-API responses, but the parser sums the
    raw amounts; refunds net out)."""
    events = {
        "ShipmentEventList": [
            {
                "ShipmentItemList": [
                    {"ItemFeeList": [{"FeeAmount": {"Amount": "-10.00"}}]},
                ],
                "ShippingChargeList": [{"ChargeAmount": {"Amount": "5.00"}}],
            }
        ],
        "RefundEventList": [
            {
                "ShipmentItemList": [
                    {"ItemFeeList": [{"FeeAmount": {"Amount": "3.00"}}]},
                ],
                "ShippingChargeList": [{"ChargeAmount": {"Amount": "-5.00"}}],
            }
        ],
    }
    result = AmazonConnector._extract_settlement_from_events(events)
    # Fees: |-10 + 3| = 7 (refund partially offset the commission)
    assert result["marketplace_fees_amount"] == pytest.approx(7.0)
    # Shipping: 5 + (-5) = 0 (full refund)
    assert result["shipping_cost_amount"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Cost-engine: apply_settlement_fees
# ---------------------------------------------------------------------------


@pytest.fixture
def ml_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    if mp is None:
        mp = Marketplace(name="MercadoLibre", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.16
    mp.default_shipping_cost = 10.0
    db.commit()
    db.refresh(mp)
    return mp


@pytest.fixture
def amazon_marketplace(db: Session) -> Marketplace:
    mp = db.query(Marketplace).filter(Marketplace.name.ilike("amazon")).first()
    if mp is None:
        mp = Marketplace(name="Amazon", api_base_url="https://example.com")
        db.add(mp)
        db.flush()
    mp.default_fee_rate = 0.15
    mp.default_shipping_cost = 5.0
    db.commit()
    db.refresh(mp)
    return mp


def _make_realized_order(
    db: Session, *, source: OrderSource, total: float, external_id: str,
) -> SalesOrder:
    """Insert a realized order with one line item; returns the order
    with a fresh estimated breakdown row attached."""
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"P-{external_id}", sku=f"SKU-{external_id}",
            default_resale_price=total, cost_price=total * 0.4,
        ),
    )
    order = SalesOrder(
        status="COMPLETED",
        total_price=total,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=source,
        external_order_id=external_id,
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=1, price_per_unit=total, cost_per_unit=total * 0.4,
    ))
    db.commit()
    db.refresh(order)
    order_cost_engine.upsert_breakdown(db, order)
    db.commit()
    return order


def test_apply_settlement_flips_source_and_overwrites_fees(db, ml_marketplace):
    """Calling apply_settlement_fees overwrites the estimated fees and
    flips fees_source to 'settled'."""
    order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-1",
    )
    breakdown = order.cost_breakdown
    assert breakdown.fees_source == "estimated"
    # 100 * 0.16 = 16, shipping 10
    assert breakdown.marketplace_fees_amount == pytest.approx(16.0)

    order_cost_engine.apply_settlement_fees(
        db, order, marketplace_fees_amount=12.34, shipping_cost_amount=7.5,
    )
    db.commit()
    db.refresh(breakdown)

    assert breakdown.fees_source == "settled"
    assert breakdown.marketplace_fees_amount == pytest.approx(12.34)
    assert breakdown.shipping_cost_amount == pytest.approx(7.5)
    assert breakdown.fees_synced_at is not None
    # Totals/profit refreshed: revenue=100, cogs=40, fees=12.34, ship=7.5
    # → total_cost=59.84, profit=40.16, margin=40.16%
    assert breakdown.total_cost_amount == pytest.approx(59.84)
    assert breakdown.net_profit_amount == pytest.approx(40.16)
    assert breakdown.net_margin_percent == pytest.approx(40.16)


def test_recompute_after_settle_preserves_settled_fees(db, ml_marketplace):
    """Once fees are settled, a subsequent recompute (e.g. operator
    bumped Marketplace.default_fee_rate) must NOT clobber the real
    settled value. COGS recompute is still allowed."""
    order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-2",
    )
    order_cost_engine.apply_settlement_fees(
        db, order, marketplace_fees_amount=12.0, shipping_cost_amount=8.0,
    )
    db.commit()

    # Operator triples the estimated rate. Recompute would normally
    # update marketplace_fees_amount to 100 * 0.48 = 48.
    ml_marketplace.default_fee_rate = 0.48
    db.commit()

    order_cost_engine.upsert_breakdown(db, order)
    db.commit()

    db.refresh(order.cost_breakdown)
    # Settled fees preserved.
    assert order.cost_breakdown.marketplace_fees_amount == pytest.approx(12.0)
    assert order.cost_breakdown.shipping_cost_amount == pytest.approx(8.0)
    assert order.cost_breakdown.fees_source == "settled"
    # COGS path still works.
    assert order.cost_breakdown.cogs_amount == pytest.approx(40.0)


def test_apply_settlement_without_shipping_only_updates_fees(db, amazon_marketplace):
    """When the marketplace's payload doesn't carry shipping (Amazon
    Commission-only event), shipping_cost_amount stays at whatever the
    engine estimated. The fees flip to settled."""
    order = _make_realized_order(
        db, source=OrderSource.AMAZON, total=100.0, external_id="AMZN-1",
    )
    breakdown = order.cost_breakdown
    estimated_shipping = breakdown.shipping_cost_amount
    assert estimated_shipping == pytest.approx(5.0)

    order_cost_engine.apply_settlement_fees(
        db, order, marketplace_fees_amount=20.0,
    )
    db.commit()
    db.refresh(breakdown)

    assert breakdown.marketplace_fees_amount == pytest.approx(20.0)
    assert breakdown.shipping_cost_amount == pytest.approx(estimated_shipping)
    assert breakdown.fees_source == "settled"


# ---------------------------------------------------------------------------
# sync_settlement_for_credential
# ---------------------------------------------------------------------------


def _build_credential(
    db: Session, *, marketplace: Marketplace, user_id: int,
) -> MarketplaceCredential:
    credential = MarketplaceCredential(
        user_id=user_id,
        marketplace_id=marketplace.id,
        access_token="encrypted-stub",
        refresh_token="encrypted-refresh",
        needs_reauthorization=False,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def test_sync_credential_flips_orders_to_settled(
    db, ml_marketplace, test_admin_user,
):
    """End-to-end: connect a credential, create one realized order,
    run sync_settlement_for_credential, the breakdown is now settled
    + last_settlement_synced_at is bumped on the credential."""
    credential = _build_credential(
        db, marketplace=ml_marketplace, user_id=test_admin_user.id,
    )
    order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-SYNC-1",
    )

    fake_connector = MagicMock(spec=MercadoLibreConnector)

    async def fake_fetch_order_billing(order_id: str, access_token: str) -> Dict[str, Any]:
        # Simulate a settled ML payload — fees + shipping
        return {
            "marketplace_fees_amount": 14.5,
            "shipping_cost_amount": 6.0,
        }

    fake_connector.fetch_order_billing = fake_fetch_order_billing

    summary = asyncio.run(
        sync_settlement_for_credential(db, credential, fake_connector, "token"),
    )
    db.commit()

    assert summary.orders_settled == 1
    assert summary.orders_pending == 0
    assert summary.errors == 0
    assert summary.scanned == 1

    db.refresh(order.cost_breakdown)
    db.refresh(credential)
    assert order.cost_breakdown.fees_source == "settled"
    assert order.cost_breakdown.marketplace_fees_amount == pytest.approx(14.5)
    assert order.cost_breakdown.shipping_cost_amount == pytest.approx(6.0)
    assert credential.last_settlement_synced_at is not None


def test_sync_credential_leaves_pending_when_marketplace_has_no_fees(
    db, ml_marketplace, test_admin_user,
):
    """When the marketplace returns None for fees (order not settled
    yet), the breakdown stays in estimated state so the next tick
    retries it."""
    credential = _build_credential(
        db, marketplace=ml_marketplace, user_id=test_admin_user.id,
    )
    order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-PEND-1",
    )

    fake_connector = MagicMock(spec=MercadoLibreConnector)

    async def fake_fetch(order_id, access_token):
        return {"marketplace_fees_amount": None, "shipping_cost_amount": None}

    fake_connector.fetch_order_billing = fake_fetch

    summary = asyncio.run(
        sync_settlement_for_credential(db, credential, fake_connector, "token"),
    )
    db.commit()

    assert summary.orders_settled == 0
    assert summary.orders_pending == 1
    assert summary.errors == 0
    db.refresh(order.cost_breakdown)
    assert order.cost_breakdown.fees_source == "estimated"


def test_sync_credential_skips_already_settled_orders(
    db, ml_marketplace, test_admin_user,
):
    """An order that's already in settled state must NOT be re-fetched
    — the loop only considers estimated rows so the API budget isn't
    wasted re-syncing what's already real."""
    credential = _build_credential(
        db, marketplace=ml_marketplace, user_id=test_admin_user.id,
    )
    order_settled = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-DONE-1",
    )
    order_cost_engine.apply_settlement_fees(
        db, order_settled, marketplace_fees_amount=9.0,
    )
    db.commit()

    fake_connector = MagicMock(spec=MercadoLibreConnector)
    calls = []

    async def fake_fetch(order_id, access_token):
        calls.append(order_id)
        return {"marketplace_fees_amount": 99.0, "shipping_cost_amount": None}

    fake_connector.fetch_order_billing = fake_fetch

    summary = asyncio.run(
        sync_settlement_for_credential(db, credential, fake_connector, "token"),
    )
    assert summary.scanned == 0
    assert calls == []


def test_sync_credential_isolates_per_order_failures(
    db, ml_marketplace, test_admin_user,
):
    """If one order's fetch raises, the loop continues with the next.
    The bad order is counted in `errors`."""
    credential = _build_credential(
        db, marketplace=ml_marketplace, user_id=test_admin_user.id,
    )
    ok_order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=100.0, external_id="ML-OK",
    )
    bad_order = _make_realized_order(
        db, source=OrderSource.MERCADOLIBRE, total=50.0, external_id="ML-BAD",
    )

    fake_connector = MagicMock(spec=MercadoLibreConnector)

    async def fake_fetch(order_id, access_token):
        if order_id == "ML-BAD":
            raise RuntimeError("ML 500")
        return {"marketplace_fees_amount": 12.0, "shipping_cost_amount": 4.0}

    fake_connector.fetch_order_billing = fake_fetch

    summary = asyncio.run(
        sync_settlement_for_credential(db, credential, fake_connector, "token"),
    )
    db.commit()

    assert summary.scanned == 2
    assert summary.orders_settled == 1
    assert summary.errors == 1
    db.refresh(ok_order.cost_breakdown)
    db.refresh(bad_order.cost_breakdown)
    assert ok_order.cost_breakdown.fees_source == "settled"
    assert bad_order.cost_breakdown.fees_source == "estimated"
