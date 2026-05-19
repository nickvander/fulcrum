"""
Schemas for the marketplace credential health surface
(`/api/v1/marketplaces/health`).

The health page is operator-facing — it answers "are my three
automatic pipelines (Amazon orders, ML orders, inbound
reconciliation) actually running?" without making the operator
ssh in to grep Celery logs.

Everything here is read-only-aggregation over existing tables;
there's no new model.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# Beat cadences are documented in `celery_worker.py`. We bake the
# staleness thresholds in here so the schema is the single source
# of truth for what the operator sees in the UI. Bump these when
# the beat schedule changes.
ORDER_POLL_STALE_MINUTES = 30      # cron fires every 15min → 30min = 2x
INBOUND_RECONCILE_STALE_MINUTES = 90  # cron fires hourly → 90min = 1.5x
# Webhook freshness: if a credential has been connected for at least
# this long AND zero webhook events have arrived for its marketplace
# in the same period, we flag the subscription as likely disconnected.
# 24h is conservative — it leaves plenty of room for low-volume
# sellers without false-positives, while still catching subscriptions
# that were never configured or that ML expired.
WEBHOOK_DISCONNECT_HOURS = 24


class MarketplaceCredentialHealth(BaseModel):
    """One row per `MarketplaceCredential`. Aggregates auth state +
    order-poll cursor + an inbound-reconciliation rollup so the UI
    can render a single status indicator per credential."""
    credential_id: int
    marketplace_id: int
    marketplace_name: str
    user_id: int

    # --- auth state ---
    needs_reauthorization: bool
    last_refresh_error: Optional[str] = None
    expires_at: Optional[datetime] = None

    # --- order poll ---
    last_orders_polled_at: Optional[datetime] = None
    orders_poll_stale: bool  # True if last_orders_polled_at is NULL or
                             # older than ORDER_POLL_STALE_MINUTES.

    # --- inbound reconciliation rollup ---
    # Open = transfer status in (SHIPPED, PARTIALLY_RECEIVED). These
    # are the only transfers the reconciler considers, so they're the
    # only ones the operator cares about for "is the poll healthy?".
    inbound_open_count: int = 0
    # Stale = open + (last_reconciled_at is NULL OR older than
    # INBOUND_RECONCILE_STALE_MINUTES). Surfaces "something has been
    # in flight for hours but the reconciler hasn't checked recently".
    inbound_stale_count: int = 0

    # --- webhook subscription freshness ---
    # ML push webhooks (and Amazon EventBridge events) land in
    # WebhookEvent. The order poller back-fills missed deliveries, so
    # the operator never sees a silent failure of the webhook channel
    # itself. These three fields surface that: when the webhook last
    # fired, how many came in over the last day, and a single derived
    # flag for "this subscription is probably broken — go check ML's
    # developer panel". Webhooks are scoped to the marketplace's app,
    # not per-user, so the marketplace-level values are repeated on
    # every credential row for the same marketplace.
    webhook_last_received_at: Optional[datetime] = None
    webhooks_received_last_24h: int = 0
    webhook_likely_disconnected: bool = False

    # --- settlement-fee ingestion ---
    # Timestamp of the last successful settlement-fee sync run for this
    # credential (Celery beat task `poll_settlement_fees`). NULL until
    # the first run completes. The marketplace-health page surfaces
    # this so the operator can tell whether the real settled-fee
    # numbers powering the dashboard's net-margin widgets are recent.
    last_settlement_synced_at: Optional[datetime] = None


class HealthListResponse(BaseModel):
    """Envelope for `GET /marketplaces/health`. The constants are
    included so the frontend can render the same staleness thresholds
    in tooltips without duplicating the numbers."""
    items: List[MarketplaceCredentialHealth]
    order_poll_stale_minutes: int = ORDER_POLL_STALE_MINUTES
    inbound_reconcile_stale_minutes: int = INBOUND_RECONCILE_STALE_MINUTES
    webhook_disconnect_hours: int = WEBHOOK_DISCONNECT_HOURS


class PollOrdersResult(BaseModel):
    """Returned by `POST /marketplaces/health/{credential_id}/poll-orders`.
    Mirrors the per-run summary shape that
    `AmazonOrderIngestionService.ingest_for_credential` and the ML
    equivalent both emit, with an `error` channel for the cases the
    bulk runner already handles (needs_reauth, missing connector).
    """
    credential_id: int
    marketplace_name: str
    orders_new: int = 0
    orders_updated: int = 0
    orders_skipped: int = 0
    items_created: int = 0
    error: Optional[str] = None
    # Refreshed health row for the caller so the UI can refresh the
    # specific credential's row without a follow-up list call.
    health: Optional[MarketplaceCredentialHealth] = None


class SettlementSyncResult(BaseModel):
    """Returned by `POST /marketplaces/health/{credential_id}/sync-settlement-fees`.

    Mirrors the per-credential `SettlementSyncSummary` shape emitted by
    `settlement_fee_ingestion.sync_settlement_for_credential` so the
    operator's manual click + the hourly Celery beat run report the
    same numbers.
    """
    credential_id: int
    marketplace_name: str
    orders_settled: int = 0       # rows flipped from estimated → settled
    orders_pending: int = 0       # marketplace had no fee data yet
    errors: int = 0
    scanned: int = 0
    error: Optional[str] = None
    health: Optional[MarketplaceCredentialHealth] = None


class ReconcileInboundResult(BaseModel):
    """Returned by `POST /marketplaces/health/{credential_id}/reconcile-inbound`.
    Aggregates the per-transfer summaries that
    `inbound_shipment_reconciliation.reconcile_for_transfer` emits
    across all open transfers for this credential's marketplace +
    user."""
    credential_id: int
    marketplace_name: str
    transfers_processed: int = 0
    transfers_updated: int = 0  # ones where items_updated > 0
    total_received_added: int = 0
    error: Optional[str] = None
    # Per-transfer summaries for the result card. Same shape as the
    # individual `POST /stock-transfers/{id}/reconcile` returns, minus
    # the embedded transfer (the operator can click through if they
    # want details).
    per_transfer: List[Dict[str, Any]] = []
    health: Optional[MarketplaceCredentialHealth] = None
