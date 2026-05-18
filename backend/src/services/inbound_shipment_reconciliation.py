"""
Inbound-shipment reconciliation.

Closes a known gap: `StockTransferService.ship(push_to_marketplace=True)`
stores an `external_inbound_id` on the StockTransfer but nothing polls
the marketplace for the actual received quantities. Operators have to
manually call `receive_items()` to advance the transfer to
PARTIALLY_RECEIVED / RECEIVED.

This module periodically polls every open ML inbound shipment and
back-fills `qty_received` from the marketplace's reported state. The
delta is applied via `inventory_service.adjust_stock` at the
transfer's `dest_location` (typically `ml-full`), so local stock
levels reflect what ML's warehouse has confirmed.

Scope: ML only today — Amazon FBA reconciliation would follow the
same shape but Amazon's inbound API is structured differently (per-
shipment item events instead of a single status poll). Land Amazon as
a follow-up.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace, MarketplaceCredential, MarketplaceListing
from src.models.stock_transfer import (
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.services.inventory_service import InventoryService
from src.services.marketplaces.base import InboundShipmentResult


logger = logging.getLogger(__name__)


_OPEN_STATUSES = (
    StockTransferStatus.SHIPPED.value,
    StockTransferStatus.PARTIALLY_RECEIVED.value,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_received_by_listing(
    result: InboundShipmentResult,
) -> Dict[str, int]:
    """Collapse the marketplace's per-line received quantities into a
    {external_listing_id: received_quantity} map. Same listing
    appearing on multiple rows (rare but possible — partial-shipment
    splits) sums into one bucket so the local reconciliation sees the
    true total.
    """
    by_listing: Dict[str, int] = {}
    for item in result.received_items:
        listing_id = item.external_listing_id
        if not listing_id:
            continue
        by_listing[listing_id] = by_listing.get(listing_id, 0) + (
            item.received_quantity or 0
        )
    return by_listing


def _build_transfer_listing_index(
    db: Session, transfer: StockTransfer, marketplace_id: int,
) -> Dict[str, StockTransferItem]:
    """Map each `external_listing_id` (ML item id) back to the local
    `StockTransferItem` that ships under it. Resolution path:
    `external_listing_id` → `marketplace_listings.product_id` →
    `stock_transfer_items.product_id`.
    """
    if not transfer.items:
        return {}
    product_ids = {item.product_id for item in transfer.items if item.product_id}
    if not product_ids:
        return {}
    listings = (
        db.query(MarketplaceListing)
        .filter(
            MarketplaceListing.marketplace_id == marketplace_id,
            MarketplaceListing.product_id.in_(product_ids),
            MarketplaceListing.external_listing_id.isnot(None),
        )
        .all()
    )
    listing_id_by_product: Dict[int, str] = {
        listing.product_id: listing.external_listing_id for listing in listings
    }
    out: Dict[str, StockTransferItem] = {}
    for item in transfer.items:
        listing_id = listing_id_by_product.get(item.product_id)
        if listing_id:
            out[listing_id] = item
    return out


def _apply_received_delta(
    db: Session,
    *,
    transfer: StockTransfer,
    transfer_item: StockTransferItem,
    delta: int,
    actor: str,
) -> None:
    """Adjust local stock + advance `qty_received` for one item by
    `delta` units. Caller guarantees `delta > 0` — we never decrement
    on reconciliation because ML reducing its reported received count
    (e.g., warehouse correction) doesn't mean Fulcrum should
    automatically yank inventory back out of `ml-full`."""
    inventory_service = InventoryService()
    inventory_service.adjust_stock(
        db=db,
        product_id=transfer_item.product_id,
        adjustment=delta,
        variant_id=transfer_item.variant_id,
        reason=(
            f"Stock transfer #{transfer.id} received at "
            f"{transfer.dest_location} (ML inbound reconciliation)"
        ),
        location=transfer.dest_location,
        user_id=actor,
    )
    transfer_item.qty_received = (transfer_item.qty_received or 0) + delta
    db.add(transfer_item)


def _update_transfer_status(transfer: StockTransfer) -> None:
    """Recompute the transfer's status from the per-item received
    counts. Same logic as `StockTransferService._apply_receiving_status`
    but inlined so the reconciliation service doesn't reach into a
    sibling service's private helper.
    """
    if not transfer.items:
        return

    all_full = True
    any_received = False
    for item in transfer.items:
        received = item.qty_received or 0
        shipped = item.qty_shipped or 0
        if received > 0:
            any_received = True
        if received < shipped:
            all_full = False

    if all_full:
        new_status = StockTransferStatus.RECEIVED.value
    elif any_received:
        new_status = StockTransferStatus.PARTIALLY_RECEIVED.value
    else:
        return  # No change.

    if new_status != transfer.status:
        from datetime import datetime, timezone
        transfer.status = new_status
        if new_status == StockTransferStatus.RECEIVED.value:
            transfer.received_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Reconciliation service
# ---------------------------------------------------------------------------


class InboundShipmentReconciliationService:
    """Stateless. Each call is a single-transfer reconciliation."""

    async def reconcile_for_transfer(
        self,
        db: Session,
        transfer: StockTransfer,
        connector,
        access_token: str,
        *,
        marketplace_id: int,
        actor: str = "ml-inbound-poll",
    ) -> Dict[str, Any]:
        """Poll the marketplace for the transfer's inbound state and
        apply any positive delta to local `qty_received` + inventory.

        Returns a summary {items_updated, total_received_added,
        status_before, status_after}. Idempotent: calling twice with no
        marketplace change is a no-op (`items_updated=0`).
        """
        summary: Dict[str, Any] = {
            "items_updated": 0,
            "total_received_added": 0,
            "status_before": transfer.status,
            "status_after": transfer.status,
        }
        if not transfer.external_inbound_id:
            summary["skipped_reason"] = "no_external_inbound_id"
            return summary
        if transfer.status not in _OPEN_STATUSES:
            summary["skipped_reason"] = f"status_{transfer.status}"
            return summary

        result: InboundShipmentResult = await connector.get_inbound_shipment_status(
            transfer.external_inbound_id,
            access_token=access_token,
        )

        received_by_listing = _build_received_by_listing(result)
        if not received_by_listing:
            return summary

        transfer_item_by_listing = _build_transfer_listing_index(
            db, transfer, marketplace_id,
        )

        for listing_id, marketplace_received in received_by_listing.items():
            item = transfer_item_by_listing.get(listing_id)
            if item is None:
                # ML reported received units for a listing we don't have
                # a local mapping for — surface as a counter instead of
                # silently dropping.
                summary.setdefault("unmapped_listings", []).append(listing_id)
                continue
            shipped = item.qty_shipped or 0
            already = item.qty_received or 0
            # Cap at the shipped quantity. Marketplace over-reporting
            # vs. what we shipped is a divergence worth logging but not
            # acting on automatically; an operator can resolve it.
            target = min(marketplace_received, shipped)
            delta = target - already
            if delta <= 0:
                continue
            _apply_received_delta(
                db,
                transfer=transfer,
                transfer_item=item,
                delta=delta,
                actor=actor,
            )
            summary["items_updated"] += 1
            summary["total_received_added"] += delta

        _update_transfer_status(transfer)
        summary["status_after"] = transfer.status
        return summary


inbound_shipment_reconciliation = InboundShipmentReconciliationService()


# ---------------------------------------------------------------------------
# Bulk runner — what the Celery beat task calls
# ---------------------------------------------------------------------------


def _open_ml_transfers(db: Session) -> List[StockTransfer]:
    """Every transfer destined for ML Full that's in flight (SHIPPED or
    PARTIALLY_RECEIVED) and has an external inbound id to poll."""
    return (
        db.query(StockTransfer)
        .filter(
            StockTransfer.status.in_(_OPEN_STATUSES),
            StockTransfer.external_inbound_id.isnot(None),
            StockTransfer.dest_location == LOCATION_ML_FULL,
        )
        .order_by(StockTransfer.id.asc())
        .all()
    )


def _ml_credential_for_transfer(
    db: Session, transfer: StockTransfer, ml_marketplace_id: int,
) -> Optional[MarketplaceCredential]:
    """Pick the ML credential that should authenticate the poll.

    Preference: the user who created the transfer
    (`StockTransfer.created_by_id`). Falls back to any healthy ML
    credential for the same marketplace if that user has no creds (or
    `created_by_id` is NULL). Returns None when no usable credential
    exists, in which case the bulk runner skips this transfer.
    """
    base = (
        db.query(MarketplaceCredential)
        .filter(
            MarketplaceCredential.marketplace_id == ml_marketplace_id,
            MarketplaceCredential.needs_reauthorization.is_(False),
            MarketplaceCredential.access_token.isnot(None),
            MarketplaceCredential.refresh_token.isnot(None),
        )
    )
    if transfer.created_by_id is not None:
        cred = base.filter(MarketplaceCredential.user_id == transfer.created_by_id).first()
        if cred is not None:
            return cred
    return base.order_by(MarketplaceCredential.updated_at.desc().nullslast()).first()


def reconcile_all_open_ml_inbounds(db: Session) -> Dict[int, Dict[str, Any]]:
    """Poll every open ML inbound shipment and apply any positive
    received-quantity delta. Per-transfer SAVEPOINT so one bad
    shipment's failure doesn't roll back another's progress.

    Returns {transfer_id: summary} so ad-hoc `.delay()` invocations
    have something readable; Beat ignores the return.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    ml_marketplace = (
        db.query(Marketplace).filter(Marketplace.name.ilike("mercadolibre")).first()
    )
    if ml_marketplace is None:
        return {}

    try:
        connector = marketplace_service.get_connector("MercadoLibre")
    except Exception:  # noqa: BLE001 — no connector → nothing to do
        logger.exception("MercadoLibre connector unavailable; skipping inbound poll")
        return {}

    results: Dict[int, Dict[str, Any]] = {}
    for transfer in _open_ml_transfers(db):
        sp = db.begin_nested()
        try:
            credential = _ml_credential_for_transfer(db, transfer, ml_marketplace.id)
            if credential is None:
                sp.rollback()
                results[transfer.id] = {"error": "no_credential"}
                logger.info(
                    "Skipping transfer %d — no usable ML credential",
                    transfer.id,
                )
                continue
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                inbound_shipment_reconciliation.reconcile_for_transfer(
                    db, transfer, connector, token,
                    marketplace_id=ml_marketplace.id,
                )
            )
            sp.commit()
            db.commit()
            results[transfer.id] = summary
            if summary.get("items_updated"):
                logger.info(
                    "Reconciled transfer %d: %s items updated, "
                    "%s units received (status %s -> %s)",
                    transfer.id,
                    summary["items_updated"],
                    summary["total_received_added"],
                    summary["status_before"],
                    summary["status_after"],
                )
        except ReauthorizationRequiredError as exc:
            sp.rollback()
            logger.warning(
                "Skipping transfer %d — credential needs reauthorization: %s",
                transfer.id, exc.reason,
            )
            results[transfer.id] = {"error": "needs_reauthorization"}
        except Exception:  # noqa: BLE001 — keep the loop alive
            sp.rollback()
            logger.exception(
                "Inbound reconciliation failed for transfer %d", transfer.id,
            )
            results[transfer.id] = {"error": "exception"}
    return results
