"""
Inbound-shipment reconciliation (marketplace-agnostic).

Closes a known gap: `StockTransferService.ship(push_to_marketplace=True)`
stores an `external_inbound_id` on the StockTransfer but nothing polls
the marketplace for the actual received quantities. Operators have to
manually call `receive_items()` to advance the transfer to
PARTIALLY_RECEIVED / RECEIVED.

The service polls every open inbound shipment for a given marketplace,
maps the marketplace's per-line received quantities back to local
`StockTransferItem` rows, and credits stock at the transfer's
`dest_location` for any positive delta. Status advances to
PARTIALLY_RECEIVED / RECEIVED automatically, `received_at` is set
when full.

Marketplaces wired today: MercadoLibre Full, Amazon FBA. The service
itself doesn't know about either — `MARKETPLACE_INBOUND_TARGETS` is the
single place that maps a marketplace name to its `dest_location` filter
and connector handle, so adding a third marketplace is just an entry
plus a connector implementation of `get_inbound_shipment_status`.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.marketplace import Marketplace, MarketplaceCredential, MarketplaceListing
from src.models.product import Product
from src.models.stock_transfer import (
    LOCATION_AMAZON_FBA,
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.services.inventory_service import InventoryService
from src.services.marketplaces.base import (
    InboundShipmentReceivedItem,
    InboundShipmentResult,
)


logger = logging.getLogger(__name__)


_OPEN_STATUSES = (
    StockTransferStatus.SHIPPED.value,
    StockTransferStatus.PARTIALLY_RECEIVED.value,
)


@dataclass(frozen=True)
class _MarketplaceTarget:
    """Single source of truth for "which marketplace owns which
    dest_location, which connector authenticates, which actor name
    shows up in the audit log."""
    marketplace_name: str   # `Marketplace.name` lookup (case-insensitive via ilike)
    connector_key: str      # `marketplace_service.get_connector(key)`
    dest_location: str      # the StockTransfer.dest_location that points here
    actor: str              # audit-log `InventoryAdjustment.created_by` value


# Registry: name → target. The Celery beat task iterates these.
# Anything not in this map is invisible to the reconciliation pipeline.
MARKETPLACE_INBOUND_TARGETS: Dict[str, _MarketplaceTarget] = {
    "mercadolibre": _MarketplaceTarget(
        marketplace_name="mercadolibre",
        connector_key="MercadoLibre",
        dest_location=LOCATION_ML_FULL,
        actor="ml-inbound-poll",
    ),
    "amazon": _MarketplaceTarget(
        marketplace_name="amazon",
        connector_key="amazon",
        dest_location=LOCATION_AMAZON_FBA,
        actor="amazon-inbound-poll",
    ),
}


def get_target_for_dest_location(dest_location: str) -> Optional[_MarketplaceTarget]:
    """Reverse lookup — `POST /stock-transfers/{id}/reconcile` resolves
    a transfer's `dest_location` to the matching marketplace target."""
    for target in MARKETPLACE_INBOUND_TARGETS.values():
        if target.dest_location == dest_location:
            return target
    return None


# ---------------------------------------------------------------------------
# Per-item resolution (listing-id first, SKU fallback)
# ---------------------------------------------------------------------------


def _resolve_received_to_product(
    db: Session,
    received: InboundShipmentReceivedItem,
    marketplace_id: int,
) -> Optional[int]:
    """Resolve one received-item row to a local `Product.id`.

    Two-step lookup so the same code path works for both ML (returns
    listing item id like `MLM123`, matched on
    `MarketplaceListing.external_listing_id`) and Amazon FBA (returns
    `SellerSKU` — which IS the local `Product.sku` for any product
    that was uploaded via the catalog or auto-listed):

    1. Try `MarketplaceListing.external_listing_id == external_listing_id`
       under the given marketplace.
    2. If that misses, try `Product.sku == received.sku` (or
       `external_listing_id` reinterpreted as SKU when no separate sku
       is supplied — Amazon's FBA inbound API only returns one
       identifier per row).

    Returns None when neither path resolves; caller logs as unmapped.
    """
    listing_id = received.external_listing_id
    if listing_id:
        listing = (
            db.query(MarketplaceListing)
            .filter(
                MarketplaceListing.marketplace_id == marketplace_id,
                MarketplaceListing.external_listing_id == str(listing_id),
            )
            .first()
        )
        if listing is not None:
            return listing.product_id

    sku_candidate = received.sku or received.external_listing_id
    if sku_candidate:
        product = db.query(Product).filter(Product.sku == str(sku_candidate)).first()
        if product is not None:
            return product.id

    return None


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
    on reconciliation because a marketplace reducing its reported
    received count (e.g., warehouse correction) doesn't mean Fulcrum
    should automatically yank inventory back out of the destination."""
    inventory_service = InventoryService()
    inventory_service.adjust_stock(
        db=db,
        product_id=transfer_item.product_id,
        adjustment=delta,
        variant_id=transfer_item.variant_id,
        reason=(
            f"Stock transfer #{transfer.id} received at "
            f"{transfer.dest_location} (inbound reconciliation)"
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
        actor: str = "inbound-poll",
    ) -> Dict[str, Any]:
        """Poll the marketplace for the transfer's inbound state and
        apply any positive delta to local `qty_received` + inventory.

        Returns a summary {items_updated, total_received_added,
        status_before, status_after}. Idempotent: calling twice with no
        marketplace change is a no-op (`items_updated=0`). On success
        the transfer's `last_reconciled_at` is bumped to the wall
        clock so the UI / health pages can show "Reconciled X ago".
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

        # Step 1: collapse the marketplace's per-line rows into a
        # {product_id: total_received} map. Each row resolves
        # independently (listing-id → product, sku fallback). Rows that
        # can't be resolved land in `unmapped_listings` for the
        # operator to investigate without blocking the rest.
        received_by_product: Dict[int, int] = {}
        for received in result.received_items:
            qty = received.received_quantity or 0
            if qty <= 0:
                continue
            product_id = _resolve_received_to_product(
                db, received, marketplace_id,
            )
            if product_id is None:
                identifier = received.external_listing_id or received.sku
                if identifier is None:
                    continue
                summary.setdefault("unmapped_listings", []).append(str(identifier))
                continue
            received_by_product[product_id] = (
                received_by_product.get(product_id, 0) + qty
            )

        # Step 2: apply the delta against each StockTransferItem.
        # `received_by_product` keys not in this transfer (marketplace
        # reported a product we didn't ship) are recorded under
        # `unmapped_listings` so the operator can see the divergence.
        items_by_product = {item.product_id: item for item in transfer.items}
        for product_id, marketplace_received in received_by_product.items():
            transfer_item = items_by_product.get(product_id)
            if transfer_item is None:
                # We resolved the listing but it's not on this transfer.
                # Surface as an unmapped row keyed by product_id so the
                # operator at least has a pointer.
                summary.setdefault("unmapped_listings", []).append(
                    f"product:{product_id}"
                )
                continue
            shipped = transfer_item.qty_shipped or 0
            already = transfer_item.qty_received or 0
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
                transfer_item=transfer_item,
                delta=delta,
                actor=actor,
            )
            summary["items_updated"] += 1
            summary["total_received_added"] += delta

        _update_transfer_status(transfer)
        transfer.last_reconciled_at = datetime.now(timezone.utc)
        summary["status_after"] = transfer.status
        return summary


inbound_shipment_reconciliation = InboundShipmentReconciliationService()


# ---------------------------------------------------------------------------
# Bulk runner — what the Celery beat tasks call
# ---------------------------------------------------------------------------


def _open_transfers_for_destination(
    db: Session, dest_location: str,
) -> List[StockTransfer]:
    """Every transfer destined for the given marketplace warehouse
    that's in flight (SHIPPED or PARTIALLY_RECEIVED) and has an
    external inbound id to poll."""
    return (
        db.query(StockTransfer)
        .filter(
            StockTransfer.status.in_(_OPEN_STATUSES),
            StockTransfer.external_inbound_id.isnot(None),
            StockTransfer.dest_location == dest_location,
        )
        .order_by(StockTransfer.id.asc())
        .all()
    )


def _credential_for_transfer(
    db: Session, transfer: StockTransfer, marketplace_id: int,
) -> Optional[MarketplaceCredential]:
    """Pick the credential that should authenticate the poll.

    Preference: the user who created the transfer
    (`StockTransfer.created_by_id`). Falls back to any healthy
    credential for the same marketplace if that user has no creds (or
    `created_by_id` is NULL). Returns None when no usable credential
    exists, in which case the bulk runner skips this transfer.
    """
    base = (
        db.query(MarketplaceCredential)
        .filter(
            MarketplaceCredential.marketplace_id == marketplace_id,
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


def reconcile_marketplace_inbounds(
    db: Session, target: _MarketplaceTarget,
) -> Dict[int, Dict[str, Any]]:
    """Poll every open inbound shipment for ONE marketplace target and
    apply any positive received-quantity delta. Per-transfer SAVEPOINT
    so one bad shipment's failure doesn't roll back another's progress.

    Returns {transfer_id: summary}. Bulk runners for individual
    marketplaces are thin wrappers around this — see
    `reconcile_all_open_ml_inbounds` / `reconcile_all_open_amazon_inbounds`.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )

    marketplace = (
        db.query(Marketplace)
        .filter(Marketplace.name.ilike(target.marketplace_name))
        .first()
    )
    if marketplace is None:
        return {}

    try:
        connector = marketplace_service.get_connector(target.connector_key)
    except Exception:  # noqa: BLE001 — no connector → nothing to do
        logger.exception(
            "%s connector unavailable; skipping inbound poll",
            target.connector_key,
        )
        return {}

    results: Dict[int, Dict[str, Any]] = {}
    for transfer in _open_transfers_for_destination(db, target.dest_location):
        sp = db.begin_nested()
        try:
            credential = _credential_for_transfer(db, transfer, marketplace.id)
            if credential is None:
                sp.rollback()
                results[transfer.id] = {"error": "no_credential"}
                logger.info(
                    "Skipping transfer %d — no usable %s credential",
                    transfer.id, target.connector_key,
                )
                continue
            token = asyncio.run(
                marketplace_service.get_valid_access_token(db, credential.id)
            )
            summary = asyncio.run(
                inbound_shipment_reconciliation.reconcile_for_transfer(
                    db, transfer, connector, token,
                    marketplace_id=marketplace.id,
                    actor=target.actor,
                )
            )
            sp.commit()
            db.commit()
            results[transfer.id] = summary
            if summary.get("items_updated"):
                logger.info(
                    "Reconciled transfer %d (%s): %s items updated, "
                    "%s units received (status %s -> %s)",
                    transfer.id, target.connector_key,
                    summary["items_updated"],
                    summary["total_received_added"],
                    summary["status_before"],
                    summary["status_after"],
                )
        except ReauthorizationRequiredError as exc:
            sp.rollback()
            logger.warning(
                "Skipping transfer %d — %s credential needs reauthorization: %s",
                transfer.id, target.connector_key, exc.reason,
            )
            results[transfer.id] = {"error": "needs_reauthorization"}
        except Exception:  # noqa: BLE001 — keep the loop alive
            sp.rollback()
            logger.exception(
                "%s inbound reconciliation failed for transfer %d",
                target.connector_key, transfer.id,
            )
            results[transfer.id] = {"error": "exception"}
    return results


def reconcile_all_open_ml_inbounds(db: Session) -> Dict[int, Dict[str, Any]]:
    """Thin wrapper kept for backwards compatibility with the existing
    Celery task name + any external callers."""
    return reconcile_marketplace_inbounds(
        db, MARKETPLACE_INBOUND_TARGETS["mercadolibre"],
    )


def reconcile_all_open_amazon_inbounds(db: Session) -> Dict[int, Dict[str, Any]]:
    """Amazon FBA equivalent — same shape as the ML helper."""
    return reconcile_marketplace_inbounds(
        db, MARKETPLACE_INBOUND_TARGETS["amazon"],
    )
