"""
Operator-facing marketplace credential health endpoints.

Surfaces:
  - GET  /marketplaces/health
  - POST /marketplaces/health/{credential_id}/poll-orders
  - POST /marketplaces/health/{credential_id}/reconcile-inbound

The page driven by these endpoints lets an operator see whether the
three automatic pipelines (Amazon order poll, ML order poll,
ML+Amazon inbound reconciliation) are healthy, and trigger them
manually for a single credential without waiting for the next
Celery beat tick.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user, get_db
from src.models.user import User
from src.schemas.marketplace_health import (
    HealthListResponse,
    PollOrdersResult,
    ReconcileInboundResult,
    SettlementSyncResult,
)
from src.services import marketplace_health_service


router = APIRouter()


@router.get("/", response_model=HealthListResponse)
def list_marketplace_health(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HealthListResponse:
    """Health rollup over every `MarketplaceCredential`. Rows ordered
    so problems land first: reauth-required credentials, then
    least-recently-polled, then by id."""
    return marketplace_health_service.list_health(db)


@router.post(
    "/{credential_id}/poll-orders",
    response_model=PollOrdersResult,
)
def poll_orders_now(
    *,
    db: Session = Depends(get_db),
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
) -> PollOrdersResult:
    """Run the per-credential order ingestion synchronously. The
    hourly Celery beat (`poll_amazon_orders` / `poll_mercadolibre_orders`)
    is the primary surface; this exists so an operator who's debugging
    can pull the current state immediately instead of waiting up to 15
    minutes for the next tick.

    Returns the per-run summary + refreshed health row so the UI can
    update without a follow-up list call.
    """
    return marketplace_health_service.poll_orders_for_credential(db, credential_id)


@router.post(
    "/{credential_id}/reconcile-inbound",
    response_model=ReconcileInboundResult,
)
def reconcile_inbound_now(
    *,
    db: Session = Depends(get_db),
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
) -> ReconcileInboundResult:
    """Run inbound reconciliation synchronously across every open
    `StockTransfer` for this credential's marketplace + user. Same
    code path as the per-transfer `POST /stock-transfers/{id}/reconcile`
    endpoint, just bulk over all the credential's open transfers."""
    return marketplace_health_service.reconcile_inbound_for_credential(
        db, credential_id,
    )


@router.post(
    "/{credential_id}/sync-settlement-fees",
    response_model=SettlementSyncResult,
)
def sync_settlement_fees_now(
    *,
    db: Session = Depends(get_db),
    credential_id: int,
    current_user: User = Depends(get_current_active_user),
) -> SettlementSyncResult:
    """Run settlement-fee ingestion synchronously for one credential.
    The hourly `poll_settlement_fees` Celery beat is the primary
    surface; this exists so an operator who just wired up real fees
    can backfill on demand instead of waiting an hour."""
    return marketplace_health_service.sync_settlement_for_credential(
        db, credential_id,
    )
