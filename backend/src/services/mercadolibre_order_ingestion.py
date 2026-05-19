"""
MercadoLibre order ingestion (delta-poll back-fill).

Mirrors `amazon_order_ingestion.py` but for ML. The primary ML order
path is the push webhook in `endpoints/webhooks.py`
(`process_mercadolibre_event`); this module exists because ML's
webhook delivery is best-effort — notifications occasionally drop or
arrive out of order. A periodic Celery beat poll back-fills any
orders the webhook missed.

Cursor: `MarketplaceCredential.last_orders_polled_at` (same column
the Amazon poller uses; shipped in migration `4c8f1d2e9b07`). NULL
on the first run → the connector falls back to a 24h lookback.

Idempotency: SalesOrder lookup is keyed by (source=MERCADOLIBRE,
external_order_id) — same key the webhook handler uses — so a poll
that races the webhook only updates status/total and never
re-decrements stock.

Multi-tenant note: this poller is naturally immune to the
multi-tenant credential-selection bug that affects the webhook
path (item 8 of `work/future/87-sales-orders-cherry-handoff.md`).
The poller iterates ONE credential at a time and authenticates with
THAT credential's access token, so each seller's orders are fetched
against their own account.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import MarketplaceCredential, MarketplaceListing
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.services.inventory_service import InventoryService
from src.services.marketplaces.mercadolibre import MercadoLibreConnector


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — ML payload → Fulcrum row mapping
#
# These were previously private to `endpoints/webhooks.py`. They've been
# lifted to this service module so both the webhook handler AND the
# poller share one implementation; `webhooks.py` re-imports them from
# here.
# ---------------------------------------------------------------------------


def ml_order_to_sales_order(payload: Dict[str, Any]) -> SalesOrder:
    """Build a fresh-insert SalesOrder row from an ML order payload.

    Status normalized to UPPER so dashboard filters
    (`status IN ("COMPLETED", "SHIPPED")`) work uniformly across
    channels. `created_at` is the ML `date_created`, parsed into a
    naive UTC datetime to match the SalesOrder TIMESTAMP column shape.
    """
    status = (payload.get("status") or "PENDING").upper()
    total_amount = payload.get("total_amount") or payload.get("paid_amount")
    date_created = payload.get("date_created")
    created_at: Optional[datetime] = None
    if isinstance(date_created, str):
        try:
            parsed = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            created_at = parsed
        except ValueError:
            created_at = None

    return SalesOrder(
        status=status,
        total_price=float(total_amount) if total_amount is not None else None,
        created_at=created_at or datetime.utcnow(),
        source=OrderSource.MERCADOLIBRE,
        external_order_id=(
            str(payload.get("id")) if payload.get("id") is not None else None
        ),
    )


def find_local_product_id(
    db: Session, marketplace_id: int, item_payload: Dict[str, Any]
) -> Optional[int]:
    """Resolve an ML order line item to a local Fulcrum product via
    marketplace_listings. ML uses `id` for the item id in the order
    line `item` object; some older payloads use `item_id`. Try both."""
    external_id = item_payload.get("id") or item_payload.get("item_id")
    if not external_id:
        return None
    listing = (
        db.query(MarketplaceListing)
        .filter(
            MarketplaceListing.marketplace_id == marketplace_id,
            MarketplaceListing.external_listing_id == str(external_id),
        )
        .first()
    )
    return listing.product_id if listing else None


def _snapshot_cost_per_unit(db: Session, product_id: Optional[int]) -> Optional[float]:
    """Capture cost-at-sale so the margin report stops drifting when
    `Product.cost_price` is later changed. NULL for unmapped lines;
    margin SQL falls back to product cost via COALESCE."""
    if product_id is None:
        return None
    from src.models.product import Product
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None or product.cost_price is None:
        return None
    return float(product.cost_price)


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------


class MercadoLibreOrderIngestionService:
    """Stateless. The only mutable state is the cursor on the credential row."""

    async def ingest_for_credential(
        self,
        db: Session,
        credential: MarketplaceCredential,
        connector: MercadoLibreConnector,
        access_token: str,
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Poll a single ML credential and upsert its new orders.

        Mirrors `AmazonOrderIngestionService.ingest_for_credential`
        contract:
          - `access_token` is passed in so the caller can wrap the call
            with `MarketplaceService.call_with_401_retry`.
          - `now` is injectable for tests so the cursor advances to a
            deterministic value.
          - Returns a per-run summary {orders_new, orders_updated,
            orders_skipped, items_created}.

        Order of operations matters: the cursor is advanced ONLY after
        every upsert in this call has landed in the session. If the
        caller rolls back (e.g. a transient DB error), the cursor stays
        where it was so the failed range gets retried on the next poll.
        """
        marketplace_id = credential.marketplace_id
        cursor = credential.last_orders_polled_at
        run_started_at = now or datetime.now(timezone.utc)

        orders = await connector.fetch_orders(
            access_token=access_token,
            created_from=cursor,
        )

        summary = {
            "orders_new": 0,
            "orders_updated": 0,
            "orders_skipped": 0,
            "items_created": 0,
        }

        inventory_service = InventoryService()

        for order_payload in orders:
            order_id = order_payload.get("id")
            if not order_id:
                summary["orders_skipped"] += 1
                continue

            external_id = str(order_id)
            existing = (
                db.query(SalesOrder)
                .filter(
                    SalesOrder.source == OrderSource.MERCADOLIBRE,
                    SalesOrder.external_order_id == external_id,
                )
                .first()
            )

            if existing is not None:
                # Refresh status + total, but DON'T re-decrement stock —
                # that already happened when the order was first
                # ingested (either via webhook or a prior poll). The
                # lifecycle hook records the audit transition, toggles
                # the breakdown's reversed_at, and re-credits stock if
                # the new status is a cancel-before-ship.
                refreshed = ml_order_to_sales_order(order_payload)
                from src.services.order_lifecycle import apply_status_change
                apply_status_change(
                    db, existing,
                    new_status=refreshed.status,
                    source_signal="ml_poll",
                )
                if refreshed.total_price is not None:
                    existing.total_price = refreshed.total_price
                summary["orders_updated"] += 1
                continue

            sales_order = ml_order_to_sales_order(order_payload)
            db.add(sales_order)
            db.flush()  # need the FK for SalesOrderItem rows below
            from src.services.order_lifecycle import record_initial_status
            record_initial_status(db, sales_order, source_signal="ml_poll")

            for line in order_payload.get("order_items", []) or []:
                item_payload = line.get("item") or {}
                try:
                    quantity = int(line.get("quantity") or 0)
                except (TypeError, ValueError):
                    quantity = 0
                unit_price_raw = line.get("unit_price")
                try:
                    price = (
                        float(unit_price_raw) if unit_price_raw is not None else None
                    )
                except (TypeError, ValueError):
                    price = None
                product_id = find_local_product_id(db, marketplace_id, item_payload)
                cost_per_unit = _snapshot_cost_per_unit(db, product_id)

                db.add(
                    SalesOrderItem(
                        order_id=sales_order.id,
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=price,
                        cost_per_unit=cost_per_unit,
                    )
                )
                summary["items_created"] += 1

                if product_id is not None and quantity > 0:
                    inventory_service.adjust_stock(
                        db,
                        product_id=product_id,
                        adjustment=-quantity,
                        reason=f"MercadoLibre order {external_id}",
                        user_id="mercadolibre-poll",
                    )

            # Phase-8 cost engine: best-effort compute breakdown so
            # the analytics rollup picks up the new order. The beat
            # backfill catches failures on the next tick.
            from src.services.order_cost_engine import upsert_breakdown_safe
            upsert_breakdown_safe(db, sales_order)

            summary["orders_new"] += 1

        credential.last_orders_polled_at = run_started_at
        return summary


mercadolibre_order_ingestion = MercadoLibreOrderIngestionService()


# ---------------------------------------------------------------------------
# Synchronous entry point for Celery
# ---------------------------------------------------------------------------


def _mercadolibre_credentials(db: Session) -> Iterable[MarketplaceCredential]:
    """Every healthy ML credential. The webhook + marketplace seeding
    paths both create the Marketplace row under different cases
    ("MercadoLibre", "mercadolibre"); `ilike` makes us indifferent."""
    from src.models.marketplace import Marketplace

    return (
        db.query(MarketplaceCredential)
        .join(Marketplace, Marketplace.id == MarketplaceCredential.marketplace_id)
        .filter(MarketplaceCredential.needs_reauthorization.is_(False))
        .filter(MarketplaceCredential.access_token.isnot(None))
        .filter(MarketplaceCredential.refresh_token.isnot(None))
        .filter(Marketplace.name.ilike("mercadolibre"))
        .all()
    )


def poll_all_mercadolibre_credentials(db: Session) -> Dict[int, Dict[str, int]]:
    """Iterate every healthy ML credential. Per-credential SAVEPOINT
    so one failed credential's writes roll back without affecting
    others (same isolation guarantee as the Amazon poller).
    Exceptions are caught + logged but never re-raised, so a bad
    credential cannot kill the Celery beat tick.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    connector = marketplace_service.get_connector("MercadoLibre")
    assert isinstance(connector, MercadoLibreConnector)

    results: Dict[int, Dict[str, int]] = {}
    for credential in _mercadolibre_credentials(db):
        sp = db.begin_nested()
        try:
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                mercadolibre_order_ingestion.ingest_for_credential(
                    db, credential, connector, token,
                )
            )
            sp.commit()
            db.commit()
            results[credential.id] = summary
            logger.info(
                "MercadoLibre order poll for credential %d: %s",
                credential.id, summary,
            )
        except ReauthorizationRequiredError as exc:
            sp.rollback()
            logger.warning(
                "Skipping MercadoLibre credential %d — needs reauthorization: %s",
                credential.id, exc.reason,
            )
            results[credential.id] = {"error": "needs_reauthorization"}
        except Exception:  # noqa: BLE001 — keep the loop alive
            sp.rollback()
            logger.exception(
                "MercadoLibre order poll failed for credential %d", credential.id,
            )
            results[credential.id] = {"error": "exception"}
    return results
