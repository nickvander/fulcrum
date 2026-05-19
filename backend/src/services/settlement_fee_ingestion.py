"""Settlement-fee ingestion.

Replace the cost engine's estimated `marketplace_fees_amount` +
`shipping_cost_amount` on `OrderCostBreakdown` rows with real settled
data fetched from each marketplace's finance API:

  - MercadoLibre: `GET /orders/{order_id}` (payments + shipping
    embedded), parsed by `MercadoLibreConnector._extract_settlement_from_order`.
  - Amazon: `GET /finances/v0/orders/{orderId}/financialEvents`,
    parsed by `AmazonConnector._extract_settlement_from_events`.

Workflow per credential:

  1. Find unsettled breakdown rows whose order belongs to the
     credential's marketplace and was created within the lookback
     window. Cap per-credential per-tick at `MAX_BATCH` so one
     hour's tick can't burn the request budget catching up a huge
     backlog — the next tick continues where this one left off.
  2. For each order, call the connector's settlement fetcher. If the
     marketplace doesn't have fee data yet (typical for pending
     shipments), skip — the order stays in `estimated` state and
     gets retried on the next tick automatically.
  3. When fees are returned, call
     `order_cost_engine.apply_settlement_fees(...)` which flips
     `fees_source` to `'settled'` and bumps `fees_synced_at`. The
     cost engine guards against subsequent recomputes overwriting
     these values.
  4. Update `credential.last_settlement_synced_at` once the loop
     finishes so the marketplace-health UI can surface freshness.

Returns a `SettlementSyncSummary` dict so the Celery task + the
manual operator endpoint share the same shape.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace, MarketplaceCredential
from src.models.order import OrderCostBreakdown, OrderSource, SalesOrder
from src.services import order_cost_engine
from src.services.marketplaces.amazon import AmazonConnector
from src.services.marketplaces.mercadolibre import MercadoLibreConnector


logger = logging.getLogger(__name__)


# Per-credential cap on orders fetched per tick. With ~hourly cadence
# and most sellers seeing 0–100 orders per day, this lets a fresh
# credential catch up its backlog within a single day even at the high
# end while bounding per-tick API budget for the steady state.
MAX_BATCH = 200

# How far back to look for orders that might still need settlement
# fetched. Settlement data typically arrives within a few days of
# shipment for ML and within a couple of weeks for Amazon FBA. Looking
# back 90 days is generous for both and still bounds the work set.
LOOKBACK_DAYS = 90


# Mirror the realized-status set the cost engine uses; settlement
# fetches on pending / cancelled orders are wasted API calls.
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED", "DELIVERED", "PAID")


@dataclass
class SettlementSyncSummary:
    """Per-credential result, used by both the Celery beat task and
    the operator-facing manual sync endpoint."""
    orders_settled: int = 0
    orders_pending: int = 0  # marketplace returned no fee data yet
    errors: int = 0
    scanned: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "orders_settled": self.orders_settled,
            "orders_pending": self.orders_pending,
            "errors": self.errors,
            "scanned": self.scanned,
        }


_SOURCE_BY_MARKETPLACE_NAME: Dict[str, OrderSource] = {
    "amazon": OrderSource.AMAZON,
    "mercadolibre": OrderSource.MERCADOLIBRE,
}


def _unsettled_orders_for_source(
    db: Session,
    source: OrderSource,
    *,
    lookback_days: int = LOOKBACK_DAYS,
    limit: int = MAX_BATCH,
) -> List[SalesOrder]:
    """Realized orders for `source`, created within the lookback
    window, whose breakdown row is still in `estimated` state (or has
    no breakdown row yet — the cost engine will create one inside
    `apply_settlement_fees`)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return (
        db.query(SalesOrder)
        .outerjoin(
            OrderCostBreakdown,
            OrderCostBreakdown.order_id == SalesOrder.id,
        )
        .filter(SalesOrder.source == source)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .filter(
            (OrderCostBreakdown.id.is_(None))
            | (
                OrderCostBreakdown.fees_source
                == order_cost_engine.ESTIMATED_FEES_SOURCE
            )
        )
        .filter(SalesOrder.external_order_id.isnot(None))
        .order_by(SalesOrder.created_at.desc())
        .limit(limit)
        .all()
    )


async def _fetch_one_mercadolibre(
    connector: MercadoLibreConnector,
    access_token: str,
    order: SalesOrder,
) -> Dict[str, Optional[float]]:
    return await connector.fetch_order_billing(order.external_order_id, access_token)


async def _fetch_one_amazon(
    connector: AmazonConnector,
    access_token: str,
    order: SalesOrder,
) -> Dict[str, Optional[float]]:
    return await connector.fetch_order_financials(order.external_order_id, access_token)


async def sync_settlement_for_credential(
    db: Session,
    credential: MarketplaceCredential,
    connector: Any,
    access_token: str,
    *,
    now: Optional[datetime] = None,
) -> SettlementSyncSummary:
    """Apply settlement fees to every unsettled order belonging to the
    credential's marketplace, capped at `MAX_BATCH` orders per call.

    Caller commits the transaction (per-credential commit pattern).
    The summary is returned even when individual orders fail so the
    operator can see partial progress.
    """
    when = now or datetime.now(timezone.utc)
    summary = SettlementSyncSummary()

    marketplace_name = (credential.marketplace.name or "").lower() if credential.marketplace else ""
    source = _SOURCE_BY_MARKETPLACE_NAME.get(marketplace_name)
    if source is None:
        logger.warning(
            "settlement-sync: credential %s has unknown marketplace name %r — skipping",
            credential.id, marketplace_name,
        )
        return summary

    if source == OrderSource.MERCADOLIBRE:
        fetch = _fetch_one_mercadolibre
    elif source == OrderSource.AMAZON:
        fetch = _fetch_one_amazon
    else:
        return summary

    orders = _unsettled_orders_for_source(db, source)
    summary.scanned = len(orders)

    for order in orders:
        try:
            settlement = await fetch(connector, access_token, order)
        except Exception:  # noqa: BLE001 — one bad order shouldn't kill the batch
            logger.exception(
                "settlement-sync: fetch failed for order %s (external_id=%s)",
                order.id, order.external_order_id,
            )
            summary.errors += 1
            continue

        fees = settlement.get("marketplace_fees_amount")
        if fees is None:
            # Marketplace hasn't settled this order yet — leave the
            # row in estimated state so the next tick retries.
            summary.orders_pending += 1
            continue

        try:
            order_cost_engine.apply_settlement_fees(
                db,
                order,
                marketplace_fees_amount=fees,
                shipping_cost_amount=settlement.get("shipping_cost_amount"),
                synced_at=when,
            )
            summary.orders_settled += 1
        except Exception:  # noqa: BLE001
            logger.exception(
                "settlement-sync: apply failed for order %s", order.id,
            )
            summary.errors += 1

    credential.last_settlement_synced_at = when
    db.flush()
    return summary


# ---------------------------------------------------------------------------
# Synchronous entry point for Celery
# ---------------------------------------------------------------------------


def _credentials_for_settlement(db: Session) -> Iterable[MarketplaceCredential]:
    """Every healthy credential for any marketplace we know how to
    settle (Amazon + MercadoLibre today). Mirrors the filter used by
    the order pollers so a reauth-required credential is silently
    skipped here too."""
    return (
        db.query(MarketplaceCredential)
        .join(Marketplace, Marketplace.id == MarketplaceCredential.marketplace_id)
        .filter(MarketplaceCredential.needs_reauthorization.is_(False))
        .filter(MarketplaceCredential.access_token.isnot(None))
        .filter(MarketplaceCredential.refresh_token.isnot(None))
        .filter(Marketplace.name.in_(["amazon", "mercadolibre", "Amazon", "MercadoLibre"]))
        .all()
    )


def poll_all_credentials_for_settlement(db: Session) -> Dict[int, Dict[str, int]]:
    """Per-credential settlement sync, commit per-credential. Returns
    `{credential_id: summary_dict}` for the caller to log. Failures on
    one credential do not abort the loop.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    results: Dict[int, Dict[str, int]] = {}
    for credential in _credentials_for_settlement(db):
        marketplace_name = (credential.marketplace.name or "").lower()
        connector = marketplace_service.get_connector(marketplace_name)
        if connector is None:
            results[credential.id] = {"error": "no_connector"}
            continue

        sp = db.begin_nested()
        try:
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id),
            )
            summary = asyncio.run(
                sync_settlement_for_credential(
                    db, credential, connector, token,
                )
            )
            sp.commit()
            db.commit()
            results[credential.id] = summary.as_dict()
            logger.info(
                "settlement-sync for credential %d: %s",
                credential.id, summary.as_dict(),
            )
        except ReauthorizationRequiredError as exc:
            sp.rollback()
            logger.warning(
                "settlement-sync: credential %d needs reauthorization: %s",
                credential.id, exc.reason,
            )
            results[credential.id] = {"error": "needs_reauthorization"}
        except Exception:  # noqa: BLE001
            sp.rollback()
            logger.exception(
                "settlement-sync failed for credential %d", credential.id,
            )
            results[credential.id] = {"error": "exception"}
    return results
