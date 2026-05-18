"""
Amazon SP-API order ingestion.

A periodic Celery beat task polls SP-API every N minutes per Amazon
MarketplaceCredential, fetches new orders, and upserts them into Fulcrum's
SalesOrder / SalesOrderItem tables. Parallels the MercadoLibre webhook
path (`api/v1/endpoints/webhooks.py::process_mercadolibre_event`) — same
SalesOrder shape, same inventory-decrement semantics — but driven by a
delta poll instead of a push notification because SP-API's webhook
surface (EventBridge) is heavier to wire up than the Orders v0 polling
API.

Cursor: `MarketplaceCredential.last_orders_polled_at` is the
`CreatedAfter` for the next run, advanced to wall-clock at the END of a
successful poll. On the first run (column is NULL), the connector falls
back to its built-in 24h default lookback.

Idempotency: SalesOrder lookups are keyed by
(source=AMAZON, external_order_id). Existing orders update status/total
only; line items + inventory adjustments are NOT re-created on a re-poll
so a fully-shipped order that gets re-fetched (e.g. after a status flip)
does not double-decrement stock.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import MarketplaceCredential, MarketplaceListing
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.services.inventory_service import inventory_service
from src.services.marketplaces.amazon import AmazonConnector


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — SP-API payload → Fulcrum row mapping
# ---------------------------------------------------------------------------


def _parse_purchase_date(raw: Optional[str]) -> datetime:
    """Parse SP-API PurchaseDate (ISO-8601 with 'Z') into a naive UTC
    datetime to match SalesOrder.created_at's TIMESTAMP column shape.
    Falls back to now-UTC if the payload is missing or malformed —
    matches `_ml_order_to_sales_order` in the ML webhook path."""
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return datetime.utcnow()


def _parse_order_total(payload: Dict[str, Any]) -> Optional[float]:
    """OrderTotal.Amount is a string in SP-API; coerce to float defensively."""
    total = payload.get("OrderTotal") or {}
    amount = total.get("Amount")
    if amount is None:
        return None
    try:
        return float(amount)
    except (TypeError, ValueError):
        return None


def _amazon_order_to_sales_order(payload: Dict[str, Any]) -> SalesOrder:
    """Build the SalesOrder row for a fresh insert. Status comes through
    upper-cased to match the convention `_ml_order_to_sales_order`
    established (so report filters like
    `status IN ("COMPLETED", "SHIPPED")` work uniformly across channels)."""
    status = (payload.get("OrderStatus") or "PENDING").upper()
    order_id = payload.get("AmazonOrderId")
    return SalesOrder(
        status=status,
        total_price=_parse_order_total(payload),
        created_at=_parse_purchase_date(payload.get("PurchaseDate")),
        source=OrderSource.AMAZON,
        external_order_id=str(order_id) if order_id is not None else None,
    )


def _resolve_product_id(
    db: Session, marketplace_id: int, item_payload: Dict[str, Any]
) -> Optional[int]:
    """Resolve a SP-API line item to a local Fulcrum product via
    marketplace_listings. SP-API gives us ASIN + SellerSKU; we try ASIN
    first because that's what fetch_all_listings stores as the
    `external_listing_id`, then fall back to SellerSKU."""
    for key in ("ASIN", "SellerSKU"):
        external_id = item_payload.get(key)
        if not external_id:
            continue
        listing = (
            db.query(MarketplaceListing)
            .filter(
                MarketplaceListing.marketplace_id == marketplace_id,
                MarketplaceListing.external_listing_id == str(external_id),
            )
            .first()
        )
        if listing is not None:
            return listing.product_id
    return None


def _parse_item_quantity(item_payload: Dict[str, Any]) -> int:
    try:
        return int(item_payload.get("QuantityOrdered") or 0)
    except (TypeError, ValueError):
        return 0


def _parse_item_price(item_payload: Dict[str, Any]) -> Optional[float]:
    price_obj = item_payload.get("ItemPrice") or {}
    amount = price_obj.get("Amount")
    if amount is None:
        return None
    try:
        return float(amount)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


class AmazonOrderIngestionService:
    """Stateless; the only mutable state is the cursor on the credential row."""

    async def ingest_for_credential(
        self,
        db: Session,
        credential: MarketplaceCredential,
        connector: AmazonConnector,
        access_token: str,
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Poll a single Amazon credential and upsert its new orders.

        `access_token` is passed in (instead of resolved inside the
        service) so the caller can run it under the
        `MarketplaceService.call_with_401_retry` wrapper without having
        to rewrite the loop here.

        `now` is injectable for tests so the cursor advances to a
        deterministic value. In production, callers omit it and the
        method reads `datetime.now(timezone.utc)`.

        Returns a per-run summary {orders_new, orders_updated, orders_skipped,
        items_created}.
        """
        marketplace_id = credential.marketplace_id
        cursor = credential.last_orders_polled_at
        run_started_at = now or datetime.now(timezone.utc)

        orders = await connector.fetch_orders(
            access_token=access_token,
            created_after=cursor,
        )

        summary = {
            "orders_new": 0,
            "orders_updated": 0,
            "orders_skipped": 0,
            "items_created": 0,
        }

        for order_payload in orders:
            order_id = order_payload.get("AmazonOrderId")
            if not order_id:
                summary["orders_skipped"] += 1
                continue

            existing = (
                db.query(SalesOrder)
                .filter(
                    SalesOrder.source == OrderSource.AMAZON,
                    SalesOrder.external_order_id == str(order_id),
                )
                .first()
            )

            if existing is not None:
                existing.status = (order_payload.get("OrderStatus") or "PENDING").upper()
                new_total = _parse_order_total(order_payload)
                if new_total is not None:
                    existing.total_price = new_total
                summary["orders_updated"] += 1
                continue

            sales_order = _amazon_order_to_sales_order(order_payload)
            db.add(sales_order)
            db.flush()  # populate sales_order.id for line items below

            items = await connector.fetch_order_items(
                order_id=str(order_id),
                access_token=access_token,
            )
            for item_payload in items:
                quantity = _parse_item_quantity(item_payload)
                price = _parse_item_price(item_payload)
                product_id = _resolve_product_id(db, marketplace_id, item_payload)

                db.add(
                    SalesOrderItem(
                        order_id=sales_order.id,
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=price,
                    )
                )
                summary["items_created"] += 1

                if product_id is not None and quantity > 0:
                    inventory_service.adjust_stock(
                        db,
                        product_id=product_id,
                        adjustment=-quantity,
                        reason=f"Amazon order {order_id}",
                        user_id="amazon-poll",
                    )

            summary["orders_new"] += 1

        # Advance the cursor once everything for this run is in the
        # session. The caller commits after the call returns; if any of
        # the upserts above raised, the caller will roll back and
        # `last_orders_polled_at` stays where it was, so the failed
        # range gets retried on the next poll.
        credential.last_orders_polled_at = run_started_at
        return summary


amazon_order_ingestion = AmazonOrderIngestionService()


# ---------------------------------------------------------------------------
# Synchronous entry point for Celery
# ---------------------------------------------------------------------------


def _amazon_credentials(db: Session) -> Iterable[MarketplaceCredential]:
    """Every credential whose marketplace name (case-insensitive) is
    "amazon". Webhook/marketplace tables seed both "Amazon" and
    "amazon" depending on the path; lower() makes us indifferent."""
    from src.models.marketplace import Marketplace

    return (
        db.query(MarketplaceCredential)
        .join(Marketplace, Marketplace.id == MarketplaceCredential.marketplace_id)
        .filter(MarketplaceCredential.needs_reauthorization.is_(False))
        .filter(MarketplaceCredential.access_token.isnot(None))
        .filter(MarketplaceCredential.refresh_token.isnot(None))
        .filter(Marketplace.name.ilike("amazon"))
        .all()
    )


def poll_all_amazon_credentials(db: Session) -> Dict[int, Dict[str, int]]:
    """Iterate every healthy Amazon credential, run the ingestion
    against each, commit per-credential so a transient failure on one
    seller's account doesn't roll back another's progress. Returns a
    {credential_id: summary} dict for the caller to log / surface.

    Failures are caught and logged but do not raise, so one bad
    credential does not kill the Celery beat tick.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    connector = marketplace_service.get_connector("amazon")
    assert isinstance(connector, AmazonConnector)

    results: Dict[int, Dict[str, int]] = {}
    for credential in _amazon_credentials(db):
        # Per-credential SAVEPOINT so one bad credential's failure
        # rolls back ONLY its writes — the outer transaction (and any
        # already-committed earlier credentials) is preserved. This
        # also keeps the Celery task playing nicely with a wrapping
        # test fixture: tests can run the whole loop inside their own
        # transactional session without our error handling tearing
        # down their setup.
        sp = db.begin_nested()
        try:
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                amazon_order_ingestion.ingest_for_credential(
                    db, credential, connector, token,
                )
            )
            sp.commit()  # release the savepoint
            db.commit()
            results[credential.id] = summary
            logger.info(
                "Amazon order poll for credential %d: %s",
                credential.id, summary,
            )
        except ReauthorizationRequiredError as exc:
            sp.rollback()
            logger.warning(
                "Skipping Amazon credential %d — needs reauthorization: %s",
                credential.id, exc.reason,
            )
            results[credential.id] = {"error": "needs_reauthorization"}
        except Exception:  # noqa: BLE001 — keep the loop alive
            sp.rollback()
            logger.exception(
                "Amazon order poll failed for credential %d", credential.id,
            )
            results[credential.id] = {"error": "exception"}
    return results
