"""Margin-floor repricing assistant (B6).

Suggests a price for each marketplace listing that hits a target net
margin, using the SKU's *real* economics: COGS plus the effective fee +
shipping rate derived from settled marketplace finance data (falling back
to the marketplace's default fee config when there's no settled history).
Flags listings priced below the floor — selling below cost is invisible
until this runs. v1 is margin-floor only; a competitor / buy-box signal
is deferred.

Margin model (per unit, price p):

    net    = p - cost - p * fee_rate - shipping
    margin = net / p

Solving margin >= floor for p:

    p_floor = (cost + shipping) / (1 - fee_rate - floor)

The denominator is the SKU's headroom: if fee_rate + floor >= 1 the floor
is unreachable at any price ("infeasible").

`apply_price` mirrors `questions_service.answer_question` — a sync wrapper
that bridges the async connector call with `asyncio.run`, returns an
error-dict, and rolls back on failure.
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace, MarketplaceListing
from src.models.order import OrderCostBreakdown, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.schemas.repricing import RepricingReport, RepricingRow

logger = logging.getLogger(__name__)

DEFAULT_MARGIN_FLOOR = 0.10
SETTLED_FEES_SOURCE = "settled"


def _effective_rates_by_source(db: Session) -> Dict[str, Tuple[float, float]]:
    """Blended (fee_rate, shipping_per_unit) per order source, from settled,
    non-reversed cost breakdowns. fee_rate folds in ad + other spend so the
    floor reflects total marketplace take, not just the headline commission.
    """
    money_rows = (
        db.query(
            SalesOrder.source,
            func.coalesce(
                func.sum(
                    OrderCostBreakdown.marketplace_fees_amount
                    + OrderCostBreakdown.ad_spend_amount
                    + OrderCostBreakdown.other_cost_amount
                ),
                0.0,
            ),
            func.coalesce(func.sum(OrderCostBreakdown.revenue_amount), 0.0),
            func.coalesce(func.sum(OrderCostBreakdown.shipping_cost_amount), 0.0),
        )
        .join(OrderCostBreakdown, OrderCostBreakdown.order_id == SalesOrder.id)
        .filter(OrderCostBreakdown.fees_source == SETTLED_FEES_SOURCE)
        .filter(OrderCostBreakdown.reversed_at.is_(None))
        .group_by(SalesOrder.source)
        .all()
    )

    # Units sold per source over the same settled orders, to turn total
    # shipping into a per-unit figure.
    unit_rows = (
        db.query(
            SalesOrder.source,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
        )
        .join(OrderCostBreakdown, OrderCostBreakdown.order_id == SalesOrder.id)
        .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
        .filter(OrderCostBreakdown.fees_source == SETTLED_FEES_SOURCE)
        .filter(OrderCostBreakdown.reversed_at.is_(None))
        .group_by(SalesOrder.source)
        .all()
    )
    units_by_source = {
        (src or "").lower(): int(u or 0) for src, u in unit_rows if src
    }

    rates: Dict[str, Tuple[float, float]] = {}
    for source, take, revenue, shipping in money_rows:
        if not source or revenue <= 0:
            continue
        key = source.lower()
        fee_rate = float(take) / float(revenue)
        units = units_by_source.get(key, 0)
        shipping_per_unit = float(shipping) / units if units > 0 else 0.0
        rates[key] = (fee_rate, shipping_per_unit)
    return rates


def _rate_for_listing(
    listing: MarketplaceListing,
    marketplace: Optional[Marketplace],
    settled_rates: Dict[str, Tuple[float, float]],
) -> Tuple[float, float, str]:
    """(fee_rate, shipping_per_unit, rate_source) for one listing — prefer
    settled data keyed by the marketplace name, else the default config."""
    name = (marketplace.name if marketplace else "").lower()
    if name in settled_rates:
        fee_rate, shipping = settled_rates[name]
        return fee_rate, shipping, "settled"
    fee_rate = float(marketplace.default_fee_rate) if marketplace else 0.0
    shipping = float(marketplace.default_shipping_cost) if marketplace else 0.0
    return fee_rate, shipping, "estimated"


def _net_margin(price: float, cost: float, fee_rate: float, shipping: float) -> Optional[float]:
    if price <= 0:
        return None
    net = price - cost - price * fee_rate - shipping
    return net / price


def build_repricing_report(
    db: Session,
    *,
    margin_floor_percent: float = DEFAULT_MARGIN_FLOOR,
    limit: int = 200,
) -> RepricingReport:
    """Per-listing margin-floor analysis. Only returns listings at risk:
    selling at a loss, under the floor, or infeasible at the current fee
    rate. Healthy listings are omitted."""
    floor = max(0.0, float(margin_floor_percent))
    settled_rates = _effective_rates_by_source(db)

    rows_q = (
        db.query(MarketplaceListing, Product, Marketplace)
        .outerjoin(Product, Product.id == MarketplaceListing.product_id)
        .outerjoin(Marketplace, Marketplace.id == MarketplaceListing.marketplace_id)
        .all()
    )

    rows: list[RepricingRow] = []
    for listing, product, marketplace in rows_q:
        price = listing.marketplace_price
        if price is None or price <= 0:
            continue
        if product is None or product.cost_price is None or product.cost_price <= 0:
            continue
        cost = float(product.cost_price)

        fee_rate, shipping, rate_source = _rate_for_listing(listing, marketplace, settled_rates)
        current_margin = _net_margin(price, cost, fee_rate, shipping)

        headroom = 1.0 - fee_rate - floor
        if headroom <= 0:
            # Floor unreachable at any price for this fee rate.
            rows.append(
                RepricingRow(
                    listing_id=listing.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    marketplace_id=listing.marketplace_id,
                    marketplace_name=marketplace.name if marketplace else "—",
                    external_listing_id=listing.external_listing_id,
                    cost_price=round(cost, 2),
                    current_price=round(float(price), 2),
                    effective_fee_rate=round(fee_rate, 4),
                    shipping_per_unit=round(shipping, 2),
                    rate_source=rate_source,
                    current_margin_percent=(
                        round(current_margin * 100, 1) if current_margin is not None else None
                    ),
                    margin_floor_percent=round(floor * 100, 1),
                    suggested_price=None,
                    suggested_margin_percent=None,
                    status="infeasible",
                )
            )
            continue

        # Healthy: at or above the floor → nothing to do.
        if current_margin is not None and current_margin >= floor:
            continue

        price_floor = (cost + shipping) / headroom
        suggested = math.ceil(price_floor * 100) / 100.0  # round up to the cent
        suggested_margin = _net_margin(suggested, cost, fee_rate, shipping)
        status = "loss" if (current_margin is not None and current_margin < 0) else "below_floor"

        rows.append(
            RepricingRow(
                listing_id=listing.id,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                marketplace_id=listing.marketplace_id,
                marketplace_name=marketplace.name if marketplace else "—",
                external_listing_id=listing.external_listing_id,
                cost_price=round(cost, 2),
                current_price=round(float(price), 2),
                effective_fee_rate=round(fee_rate, 4),
                shipping_per_unit=round(shipping, 2),
                rate_source=rate_source,
                current_margin_percent=(
                    round(current_margin * 100, 1) if current_margin is not None else None
                ),
                margin_floor_percent=round(floor * 100, 1),
                suggested_price=round(suggested, 2),
                suggested_margin_percent=(
                    round(suggested_margin * 100, 1) if suggested_margin is not None else None
                ),
                status=status,
            )
        )

    # Worst first: losses, then thinnest margin.
    status_order = {"loss": 0, "below_floor": 1, "infeasible": 2}
    rows.sort(
        key=lambda r: (
            status_order.get(r.status, 9),
            r.current_margin_percent if r.current_margin_percent is not None else 999.0,
        )
    )

    return RepricingReport(
        rows=rows[:limit],
        margin_floor_percent=round(floor * 100, 1),
        total_loss=sum(1 for r in rows if r.status == "loss"),
        total_below_floor=sum(1 for r in rows if r.status in ("loss", "below_floor")),
    )


def apply_price(db: Session, *, listing_id: int, price: float, user_id: int) -> Dict[str, Any]:
    """Push a new price to the marketplace and persist it on the listing.

    Mirrors `questions_service.answer_question`: a sync wrapper that bridges
    the async connector call with `asyncio.run` and returns an error-dict.

      - unknown listing / no external id → {"error": "not_found"}
      - non-priceable price              → {"error": "invalid_price"}
      - no credential for the marketplace → {"error": "no_credentials"}
      - credential needs reauth          → {"error": "needs_reauthorization"}
      - connector rejected / unsupported  → {"error": "unsupported"}
      - any other failure                → rollback + {"error": "exception"}

    On success returns {"listing": <model>}.
    """
    if price is None or price <= 0:
        return {"error": "invalid_price"}

    listing = (
        db.query(MarketplaceListing)
        .filter(MarketplaceListing.id == listing_id)
        .first()
    )
    if listing is None or not listing.external_listing_id:
        return {"error": "not_found"}

    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == listing.marketplace_id).first()
    )
    if marketplace is None:
        return {"error": "not_found"}

    from src.crud.crud_marketplace_credential import (
        marketplace_credential as crud_cred,
    )
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    credential = crud_cred.get_by_marketplace(
        db, user_id=user_id, marketplace_id=listing.marketplace_id
    )
    if credential is None:
        return {"error": "no_credentials"}
    if credential.needs_reauthorization:
        return {"error": "needs_reauthorization"}

    connector = marketplace_service.get_connector(marketplace.name)

    try:
        ok = asyncio.run(
            marketplace_service.call_with_401_retry(
                db,
                credential.id,
                lambda token: connector.sync_price(
                    listing.external_listing_id, float(price), access_token=token
                ),
            )
        )
        if not ok:
            db.rollback()
            return {"error": "unsupported"}
        listing.marketplace_price = float(price)
        db.commit()
        db.refresh(listing)
    except ReauthorizationRequiredError:
        db.rollback()
        return {"error": "needs_reauthorization"}
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("Apply price failed for listing %d", listing_id)
        return {"error": "exception"}
    return {"listing": listing}
