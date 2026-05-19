import asyncio
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user
from src.core.errors import LocalizedHTTPException
from src.crud.crud_stock_transfer import stock_transfer as crud_stock_transfer
from src.database import get_db
from src.models.marketplace import Marketplace
from src.models.user import User
from src.schemas import stock_transfer as st_schema
from src.services.inbound_shipment_reconciliation import (
    get_target_for_dest_location,
    inbound_shipment_reconciliation,
)
from src.services.stock_transfer_service import stock_transfer_service

router = APIRouter()


@router.get("/inventory-snapshot", response_model=List[st_schema.InventorySnapshotRow])
def stock_transfer_inventory_snapshot(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Per-product stock broken down by internal vs marketplace-warehouse
    locations. Feeds the allocation planner.
    """
    return stock_transfer_service.get_inventory_snapshot(db=db)


@router.get("/reconciliation", response_model=List[st_schema.ReconciliationRow])
def stock_transfer_reconciliation(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Lines from completed / cancelled / partial transfers where received qty
    diverges from shipped qty — i.e., shrinkage, damage, or over-receipt.
    """
    return stock_transfer_service.get_reconciliation_report(db=db)


@router.post(
    "/plan-allocations",
    response_model=List[st_schema.StockTransfer],
)
def plan_allocations(
    *,
    db: Session = Depends(get_db),
    plan: st_schema.StockAllocationPlanRequest,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create one DRAFT transfer per destination location from a flat list of
    {product_id, dest_location, qty_planned} allocations. Validates that the
    combined draft allocations don't exceed the current internal stock.
    """
    return stock_transfer_service.plan_allocations(
        db=db,
        allocations=[a.model_dump() for a in plan.allocations],
        notes=plan.notes,
        user=current_user,
    )


@router.post("/", response_model=st_schema.StockTransfer)
def create_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_in: st_schema.StockTransferCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return stock_transfer_service.create_draft(
        db=db, transfer_in=transfer_in, user=current_user
    )


@router.get("/", response_model=List[st_schema.StockTransfer])
def list_stock_transfers(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return crud_stock_transfer.get_multi(db=db, skip=skip, limit=limit, status=status)


@router.get("/{transfer_id}", response_model=st_schema.StockTransfer)
def read_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    transfer = crud_stock_transfer.get(db=db, id=transfer_id)
    if not transfer:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.stockTransfer.notFound",
            params={"id": transfer_id},
            detail="Stock transfer not found",
        )
    return transfer


@router.put("/{transfer_id}", response_model=st_schema.StockTransfer)
def update_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    transfer_in: st_schema.StockTransferUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return stock_transfer_service.update_draft(
        db=db, transfer_id=transfer_id, transfer_in=transfer_in
    )


@router.post("/{transfer_id}/ship", response_model=st_schema.StockTransfer)
def ship_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    push_to_marketplace: bool = Query(
        False,
        description=(
            "When true and the destination is ml-full / amazon-fba, also "
            "create an inbound shipment via the marketplace's API and store "
            "the resulting external_inbound_id."
        ),
    ),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return stock_transfer_service.ship(
        db=db,
        transfer_id=transfer_id,
        user=current_user,
        push_to_marketplace=push_to_marketplace,
    )


@router.post("/{transfer_id}/sync-listings")
def sync_stock_transfer_listings(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Push the destination-location quantity to every MarketplaceListing for
    products in this transfer. Typically called after a transfer reaches
    RECEIVED to update the marketplace's published inventory.
    """
    return stock_transfer_service.sync_marketplace_listings(
        db=db, transfer_id=transfer_id, user=current_user
    )


@router.post("/{transfer_id}/receive", response_model=st_schema.StockTransfer)
def receive_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    received_items: List[st_schema.StockTransferReceiveItem],
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return stock_transfer_service.receive_items(
        db=db,
        transfer_id=transfer_id,
        received_items=received_items,
        user=current_user,
    )


@router.post(
    "/{transfer_id}/reconcile",
    response_model=st_schema.ReconcileResult,
)
def reconcile_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Force-run inbound reconciliation for a single transfer.

    The hourly Celery beat (`reconcile_ml_inbound_shipments` /
    `reconcile_amazon_inbound_shipments`) handles the background path;
    this endpoint exists so an operator who knows the warehouse just
    received a shipment can pull the new state immediately instead of
    waiting up to an hour for the next tick.

    Resolves the marketplace via the `dest_location` registry in
    `inbound_shipment_reconciliation` so the same endpoint serves both
    ML Full and Amazon FBA transfers. Returns the per-transfer summary
    plus the freshly-updated row so the UI doesn't need a follow-up
    GET.
    """
    from src.services.marketplace_service import (
        ReauthorizationRequiredError,
        marketplace_service,
    )
    from src.services.inbound_shipment_reconciliation import (
        _credential_for_transfer,
    )

    transfer = crud_stock_transfer.get(db=db, id=transfer_id)
    if not transfer:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.stockTransfer.notFound",
            params={"id": transfer_id},
            detail="Stock transfer not found",
        )

    target = get_target_for_dest_location(transfer.dest_location)
    if target is None:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.stockTransfer.reconcileUnsupportedDestination",
            params={"dest": transfer.dest_location},
            detail=(
                f"Destination '{transfer.dest_location}' is not a known "
                f"marketplace fulfillment warehouse"
            ),
        )

    marketplace = (
        db.query(Marketplace)
        .filter(Marketplace.name.ilike(target.marketplace_name))
        .first()
    )
    if marketplace is None:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.stockTransfer.reconcileMarketplaceNotFound",
            params={"name": target.connector_key},
            detail=f"Marketplace '{target.connector_key}' is not configured",
        )

    credential = _credential_for_transfer(db, transfer, marketplace.id)
    if credential is None:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.stockTransfer.reconcileNoCredential",
            params={"name": target.connector_key},
            detail=(
                f"No usable {target.connector_key} credential for this "
                f"transfer. Connect the marketplace before reconciling."
            ),
        )

    try:
        connector = marketplace_service.get_connector(target.connector_key)
    except Exception as exc:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.stockTransfer.reconcileConnectorUnavailable",
            params={"name": target.connector_key},
            detail=f"Marketplace connector unavailable: {exc}",
        )

    try:
        token = asyncio.run(
            marketplace_service.get_valid_access_token(db, credential.id)
        )
    except ReauthorizationRequiredError as exc:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.stockTransfer.reconcileNeedsReauth",
            params={"name": target.connector_key, "reason": exc.reason},
            detail=f"{target.connector_key} credential needs reauthorization: {exc.reason}",
        )

    summary = asyncio.run(
        inbound_shipment_reconciliation.reconcile_for_transfer(
            db, transfer, connector, token,
            marketplace_id=marketplace.id,
            actor=target.actor,
        )
    )
    db.commit()
    db.refresh(transfer)

    return st_schema.ReconcileResult(
        items_updated=summary.get("items_updated", 0),
        total_received_added=summary.get("total_received_added", 0),
        status_before=summary.get("status_before", transfer.status),
        status_after=summary.get("status_after", transfer.status),
        skipped_reason=summary.get("skipped_reason"),
        unmapped_listings=summary.get("unmapped_listings", []),
        transfer=transfer,
    )


@router.post("/{transfer_id}/cancel", response_model=st_schema.StockTransfer)
def cancel_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return stock_transfer_service.cancel(db=db, transfer_id=transfer_id)


@router.delete("/{transfer_id}")
def delete_stock_transfer(
    *,
    db: Session = Depends(get_db),
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    stock_transfer_service.delete_draft(db=db, transfer_id=transfer_id)
    return {"deleted": transfer_id}
