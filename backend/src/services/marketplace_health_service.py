"""
Marketplace credential health aggregation.

Read-only-ish: builds a per-credential health row from the existing
`MarketplaceCredential` columns plus a rollup of in-flight
`StockTransfer` rows. Used by the operator-facing
`/marketplaces/health` page to answer:

  - Which credentials need reauth?
  - Is each credential's order poll cursor advancing on schedule?
  - Are any in-flight inbound shipments stuck waiting on the hourly
    reconciler?

The page also exposes "Poll now" / "Reconcile now" actions that hit
the per-credential entrypoints on the existing ingestion +
reconciliation services. Those entrypoints are reused as-is so the
manual + automatic paths share one implementation.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace, MarketplaceCredential
from src.models.stock_transfer import (
    StockTransfer,
    StockTransferStatus,
)
from src.schemas.marketplace_health import (
    HealthListResponse,
    INBOUND_RECONCILE_STALE_MINUTES,
    MarketplaceCredentialHealth,
    ORDER_POLL_STALE_MINUTES,
    PollOrdersResult,
    ReconcileInboundResult,
)


logger = logging.getLogger(__name__)


# Map (case-insensitive) marketplace name → dest_location used by the
# inbound reconciler. Single source of truth so the health rollup and
# the reconciler agree on what counts as "this credential's open
# transfers".
_MARKETPLACE_TO_DEST_LOCATION: Dict[str, str] = {
    "mercadolibre": "ml-full",
    "amazon": "amazon-fba",
}


_OPEN_TRANSFER_STATUSES = (
    StockTransferStatus.SHIPPED.value,
    StockTransferStatus.PARTIALLY_RECEIVED.value,
)


def _is_order_poll_stale(
    last_polled_at: Optional[datetime], now: datetime,
) -> bool:
    """A credential's order poll is stale when the cursor has never
    advanced OR it last advanced more than ORDER_POLL_STALE_MINUTES
    ago. Beat fires every 15min, so ~30min flags the operator that
    something is wrong (token rotation broke, ML / SP-API down, beat
    not running, etc.)."""
    if last_polled_at is None:
        return True
    # `last_orders_polled_at` is timezone-aware (DateTime(timezone=True));
    # `now` should be too. If it isn't, normalize to UTC.
    if last_polled_at.tzinfo is None:
        last_polled_at = last_polled_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - last_polled_at) > timedelta(minutes=ORDER_POLL_STALE_MINUTES)


def _dest_location_for(marketplace_name: str) -> Optional[str]:
    return _MARKETPLACE_TO_DEST_LOCATION.get(marketplace_name.lower())


def _open_transfer_stats(
    db: Session, marketplace_name: str, user_id: Optional[int],
) -> Dict[str, int]:
    """Count open transfers for this marketplace (filtered to the
    credential's user when possible, otherwise all opens — pre-multi-
    tenant credentials have NULL user_id on a few rows).

    Returns {open_count, stale_count}. Stale is the count of open
    transfers whose `last_reconciled_at` is NULL or older than
    INBOUND_RECONCILE_STALE_MINUTES. Beat fires hourly so 90min flags
    a stuck reconciler.
    """
    dest = _dest_location_for(marketplace_name)
    if dest is None:
        return {"open_count": 0, "stale_count": 0}

    base = db.query(StockTransfer).filter(
        StockTransfer.status.in_(_OPEN_TRANSFER_STATUSES),
        StockTransfer.external_inbound_id.isnot(None),
        StockTransfer.dest_location == dest,
    )
    if user_id is not None:
        base = base.filter(StockTransfer.created_by_id == user_id)

    open_count = base.count()

    stale_cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=INBOUND_RECONCILE_STALE_MINUTES,
    )
    stale_count = base.filter(
        (StockTransfer.last_reconciled_at.is_(None))
        | (StockTransfer.last_reconciled_at < stale_cutoff)
    ).count()

    return {"open_count": open_count, "stale_count": stale_count}


def _build_credential_health(
    db: Session, credential: MarketplaceCredential, now: datetime,
) -> MarketplaceCredentialHealth:
    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    marketplace_name = marketplace.name if marketplace else f"#{credential.marketplace_id}"

    stats = _open_transfer_stats(db, marketplace_name, credential.user_id)
    return MarketplaceCredentialHealth(
        credential_id=credential.id,
        marketplace_id=credential.marketplace_id,
        marketplace_name=marketplace_name,
        user_id=credential.user_id,
        needs_reauthorization=bool(credential.needs_reauthorization),
        last_refresh_error=credential.last_refresh_error,
        expires_at=credential.expires_at,
        last_orders_polled_at=credential.last_orders_polled_at,
        orders_poll_stale=_is_order_poll_stale(
            credential.last_orders_polled_at, now,
        ),
        inbound_open_count=stats["open_count"],
        inbound_stale_count=stats["stale_count"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_health(db: Session) -> HealthListResponse:
    """Build the health rollup over every existing credential.
    Ordered so the operator's eye lands on problems first: rows whose
    auth is broken or whose poll is stale come before healthy ones.
    """
    credentials = (
        db.query(MarketplaceCredential)
        .order_by(
            MarketplaceCredential.needs_reauthorization.desc(),
            MarketplaceCredential.last_orders_polled_at.asc().nullsfirst(),
            MarketplaceCredential.id.asc(),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    items = [_build_credential_health(db, c, now) for c in credentials]
    return HealthListResponse(items=items)


def get_credential_or_raise(
    db: Session, credential_id: int,
) -> MarketplaceCredential:
    """Lookup helper shared by the action endpoints. Raises a
    standard 404 via `LocalizedHTTPException` so all three endpoints
    surface the same error shape."""
    from src.core.errors import LocalizedHTTPException

    credential = (
        db.query(MarketplaceCredential)
        .filter(MarketplaceCredential.id == credential_id)
        .first()
    )
    if credential is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredential.notFound",
            params={"id": credential_id},
            detail=f"Marketplace credential {credential_id} not found",
        )
    return credential


def poll_orders_for_credential(
    db: Session, credential_id: int,
) -> PollOrdersResult:
    """Run the per-credential order ingestion synchronously and
    return the summary. Reuses the same per-credential entrypoint
    the Celery beat task does
    (`{amazon,mercadolibre}_order_ingestion.ingest_for_credential`)
    so the manual + automatic paths cannot drift.

    Synchronous on purpose — the operator clicks this expecting
    "did anything new come in?". A typical 15-min delta is < 5s
    against ML's order search. If it ever gets slow, flip to
    `.delay()` and add a status-polling UI; not worth the complexity
    today.
    """
    credential = get_credential_or_raise(db, credential_id)
    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    marketplace_name = marketplace.name if marketplace else ""

    result = PollOrdersResult(
        credential_id=credential.id,
        marketplace_name=marketplace_name,
    )

    if credential.needs_reauthorization:
        result.error = "needs_reauthorization"
        result.health = _build_credential_health(
            db, credential, datetime.now(timezone.utc),
        )
        return result

    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    name_lower = (marketplace_name or "").lower()
    if name_lower == "amazon":
        from src.services.amazon_order_ingestion import amazon_order_ingestion
        from src.services.marketplaces.amazon import AmazonConnector

        connector = marketplace_service.get_connector("amazon")
        if not isinstance(connector, AmazonConnector):
            result.error = "connector_unavailable"
            return result
        try:
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                amazon_order_ingestion.ingest_for_credential(
                    db, credential, connector, token,
                )
            )
            db.commit()
        except ReauthorizationRequiredError as exc:
            result.error = "needs_reauthorization"
            logger.warning(
                "Manual poll: Amazon credential %d needs reauth: %s",
                credential.id, exc.reason,
            )
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception(
                "Manual Amazon poll failed for credential %d", credential.id,
            )
            result.error = "exception"
        else:
            result.orders_new = int(summary.get("orders_new", 0))
            result.orders_updated = int(summary.get("orders_updated", 0))
            result.orders_skipped = int(summary.get("orders_skipped", 0))
            result.items_created = int(summary.get("items_created", 0))
    elif name_lower == "mercadolibre":
        from src.services.marketplaces.mercadolibre import MercadoLibreConnector
        from src.services.mercadolibre_order_ingestion import (
            mercadolibre_order_ingestion,
        )

        connector = marketplace_service.get_connector("MercadoLibre")
        if not isinstance(connector, MercadoLibreConnector):
            result.error = "connector_unavailable"
            return result
        try:
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                mercadolibre_order_ingestion.ingest_for_credential(
                    db, credential, connector, token,
                )
            )
            db.commit()
        except ReauthorizationRequiredError as exc:
            result.error = "needs_reauthorization"
            logger.warning(
                "Manual poll: ML credential %d needs reauth: %s",
                credential.id, exc.reason,
            )
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception(
                "Manual ML poll failed for credential %d", credential.id,
            )
            result.error = "exception"
        else:
            result.orders_new = int(summary.get("orders_new", 0))
            result.orders_updated = int(summary.get("orders_updated", 0))
            result.orders_skipped = int(summary.get("orders_skipped", 0))
            result.items_created = int(summary.get("items_created", 0))
    else:
        # A custom marketplace with no order-polling path. Surfaced as
        # an error code instead of a 4xx so the UI can render a clear
        # "Order polling isn't supported for {name}" message.
        result.error = "unsupported_marketplace"

    db.refresh(credential)
    result.health = _build_credential_health(
        db, credential, datetime.now(timezone.utc),
    )
    return result


def reconcile_inbound_for_credential(
    db: Session, credential_id: int,
) -> ReconcileInboundResult:
    """Run inbound reconciliation synchronously across every open
    StockTransfer that belongs to this credential's user +
    marketplace destination. Returns aggregate counters + per-
    transfer summaries so the operator can see what changed.
    """
    credential = get_credential_or_raise(db, credential_id)
    marketplace = (
        db.query(Marketplace).filter(Marketplace.id == credential.marketplace_id).first()
    )
    marketplace_name = marketplace.name if marketplace else ""

    result = ReconcileInboundResult(
        credential_id=credential.id,
        marketplace_name=marketplace_name,
    )

    if credential.needs_reauthorization:
        result.error = "needs_reauthorization"
        result.health = _build_credential_health(
            db, credential, datetime.now(timezone.utc),
        )
        return result

    dest_location = _dest_location_for(marketplace_name)
    if dest_location is None:
        result.error = "unsupported_marketplace"
        result.health = _build_credential_health(
            db, credential, datetime.now(timezone.utc),
        )
        return result

    open_transfers = (
        db.query(StockTransfer)
        .filter(
            StockTransfer.status.in_(_OPEN_TRANSFER_STATUSES),
            StockTransfer.external_inbound_id.isnot(None),
            StockTransfer.dest_location == dest_location,
            (StockTransfer.created_by_id == credential.user_id)
            | (StockTransfer.created_by_id.is_(None)),
        )
        .order_by(StockTransfer.id.asc())
        .all()
    )

    if not open_transfers:
        result.health = _build_credential_health(
            db, credential, datetime.now(timezone.utc),
        )
        return result

    from src.services.inbound_shipment_reconciliation import (
        MARKETPLACE_INBOUND_TARGETS,
        inbound_shipment_reconciliation,
    )
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    target = MARKETPLACE_INBOUND_TARGETS.get(marketplace_name.lower())
    if target is None:
        result.error = "unsupported_marketplace"
        return result

    try:
        connector = marketplace_service.get_connector(target.connector_key)
    except Exception:  # noqa: BLE001
        result.error = "connector_unavailable"
        return result

    try:
        token = asyncio.run(
            marketplace_service.get_valid_access_token(db, credential.id)
        )
    except ReauthorizationRequiredError as exc:
        result.error = "needs_reauthorization"
        logger.warning(
            "Manual reconcile: credential %d needs reauth: %s",
            credential.id, exc.reason,
        )
        result.health = _build_credential_health(
            db, credential, datetime.now(timezone.utc),
        )
        return result

    per_transfer: List[Dict[str, Any]] = []
    transfers_updated = 0
    total_received_added = 0

    for transfer in open_transfers:
        sp = db.begin_nested()
        try:
            summary = asyncio.run(
                inbound_shipment_reconciliation.reconcile_for_transfer(
                    db, transfer, connector, token,
                    marketplace_id=credential.marketplace_id,
                    actor=target.actor,
                )
            )
            sp.commit()
            db.commit()
        except Exception:  # noqa: BLE001 — one bad transfer shouldn't
                           # kill the loop
            sp.rollback()
            logger.exception(
                "Manual reconcile failed for transfer %d", transfer.id,
            )
            per_transfer.append({
                "transfer_id": transfer.id,
                "error": "exception",
            })
            continue
        if summary.get("items_updated", 0) > 0:
            transfers_updated += 1
            total_received_added += summary["total_received_added"]
        per_transfer.append({
            "transfer_id": transfer.id,
            "items_updated": summary.get("items_updated", 0),
            "total_received_added": summary.get("total_received_added", 0),
            "status_before": summary.get("status_before"),
            "status_after": summary.get("status_after"),
            "skipped_reason": summary.get("skipped_reason"),
            "unmapped_listings": summary.get("unmapped_listings", []),
        })

    result.transfers_processed = len(open_transfers)
    result.transfers_updated = transfers_updated
    result.total_received_added = total_received_added
    result.per_transfer = per_transfer
    db.refresh(credential)
    result.health = _build_credential_health(
        db, credential, datetime.now(timezone.utc),
    )
    return result
