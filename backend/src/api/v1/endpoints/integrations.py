"""
Integrations API endpoints for data export and Google Sheets sync.

This module provides:
1. Universal data export (CSV, JSON, XLSX)
2. Google Sheets bidirectional sync endpoints
3. API key management for external tool authentication
"""
from fastapi import APIRouter, Depends, Query, Response, HTTPException, Security
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime
from collections import defaultdict
import csv
import io
import json
import secrets
import hashlib

from src.database import get_db
from src.crud.crud_product import product as crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.api import dependencies

from src.models.user import User
from src.models.api_key import ApiKey
from src.models.pending_sync import SyncBatch, PendingSyncChange, EntityChangeLog

router = APIRouter()


# =============================================================================
# Pydantic Schemas for Integrations
# =============================================================================

class ExportRequest(BaseModel):
    """Request body for export operations."""
    format: Literal["csv", "json", "xlsx"] = "csv"
    entity: Literal["products", "suppliers", "inventory"]
    filters: Optional[dict] = None


class SheetsSyncPullRequest(BaseModel):
    """Request from Google Sheets to pull data from Fulcrum."""
    entity: Literal["products", "inventory", "suppliers", "purchase-orders", "expenses"]
    last_sync_timestamp: Optional[datetime] = None


class SheetsSyncPullResponse(BaseModel):
    """Response for Sheets pull operation."""
    data: List[dict]
    sync_timestamp: datetime
    total_records: int


class SheetsSyncPushRequest(BaseModel):
    """Request from Google Sheets to push changes to Fulcrum."""
    entity: Literal["products", "inventory"]
    changes: List[dict]  # Each dict has: id, field, new_value


class SheetsSyncPushResponse(BaseModel):
    """Response for Sheets push operation - changes staged for approval."""
    success: bool
    batch_id: int  # ID of the created SyncBatch for tracking
    staged_count: int  # Number of changes staged
    message: str  # User-friendly message
    errors: List[str] = []


# --- Pending Sync Review Schemas ---

class PendingChangeInfo(BaseModel):
    """Individual pending change for preview."""
    id: int
    entity_id: int
    entity_name: Optional[str]
    entity_sku: Optional[str]
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    status: str


class PendingBatchInfo(BaseModel):
    """Batch of pending changes."""
    id: int
    source: str
    status: str
    total_changes: int
    approved_count: int
    rejected_count: int
    created_at: datetime
    changes: List[PendingChangeInfo]


class PendingBatchListResponse(BaseModel):
    """Response for listing pending batches."""
    batches: List[PendingBatchInfo]
    total_pending: int


class SyncApproveRequest(BaseModel):
    """Request to approve/reject specific changes."""
    batch_id: int
    change_ids: List[int]  # IDs of PendingSyncChange to approve
    action: Literal["approve", "reject"]


class SyncApproveResponse(BaseModel):
    """Response after approving/rejecting changes."""
    success: bool
    applied_count: int
    message: str
    errors: List[str] = []


# --- Entity Change Log Schemas ---

class ChangeLogEntry(BaseModel):
    """Entry in the entity change log."""
    id: int
    entity_type: str
    entity_id: int
    entity_name: Optional[str]
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    source: str
    changed_by_email: Optional[str]
    changed_at: datetime


class ChangeLogResponse(BaseModel):
    """Response for change log queries."""
    entries: List[ChangeLogEntry]
    total: int


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export/products")
async def export_products(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    Export all products in the specified format.
    
    Supports: CSV, JSON
    """
    products = crud_product.get_multi(db, skip=0, limit=10000)
    
    if format == "json":
        data = [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "cost_price": p.cost_price,
                "default_resale_price": p.default_resale_price,
                "manufacturer": p.manufacturer,
                "brand": p.brand,
                "category": p.category,
                "stock_quantity": sum(i.quantity for i in p.inventory_items) if p.inventory_items else 0,
                "is_bundle": p.is_bundle,
            }
            for p in products
        ]
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=products_export.json"}
        )
    
    # CSV format (default)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    headers = ["ID", "SKU", "Name", "Description", "Cost Price", "Resale Price", 
               "Manufacturer", "Brand", "Category", "Stock Quantity", "Is Bundle"]
    writer.writerow(headers)
    
    # Data rows
    for p in products:
        stock = sum(i.quantity for i in p.inventory_items) if p.inventory_items else 0
        writer.writerow([
            p.id, p.sku, p.name, p.description or "", p.cost_price or 0,
            p.default_resale_price or 0, p.manufacturer or "", p.brand or "",
            p.category or "", stock, p.is_bundle
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_export.csv"}
    )


@router.get("/export/suppliers")
async def export_suppliers(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Export all suppliers in the specified format."""
    suppliers = crud_supplier.get_multi(db, skip=0, limit=10000)
    
    if format == "json":
        data = [
            {
                "id": s.id,
                "name": s.name,
                "contact_person": s.contact_person,
                "email": s.email,
                "phone": s.phone,
            }
            for s in suppliers
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=suppliers_export.json"}
        )
    
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Contact Person", "Email", "Phone"])
    for s in suppliers:
        writer.writerow([s.id, s.name, s.contact_person or "", s.email or "", s.phone or ""])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=suppliers_export.csv"}
    )


@router.get("/export/inventory")
async def export_inventory(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Export inventory levels for all products."""
    products = crud_product.get_multi(db, skip=0, limit=10000)
    
    inventory_data = []
    for p in products:
        stock = sum(i.quantity for i in p.inventory_items) if p.inventory_items else 0
        inventory_data.append({
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "stock_quantity": stock,
            "cost_price": p.cost_price or 0,
            "average_cost": p.average_cost or p.cost_price or 0,
        })
    
    if format == "json":
        return Response(
            content=json.dumps(inventory_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=inventory_export.json"}
        )
    
    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product ID", "SKU", "Name", "Stock Quantity", "Cost Price", "Average Cost"])
    for item in inventory_data:
        writer.writerow([
            item["product_id"], item["sku"], item["name"],
            item["stock_quantity"], item["cost_price"], item["average_cost"]
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_export.csv"}
    )


@router.get("/export/purchase-orders")
async def export_purchase_orders(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Export all purchase orders in the specified format."""
    from src.models.purchase_order import PurchaseOrder
    
    orders = db.query(PurchaseOrder).limit(10000).all()
    
    data = []
    for po in orders:
        data.append({
            "id": po.id,
            "po_number": po.po_number,
            "supplier_id": po.supplier_id,
            "status": po.status,
            "total_amount": float(po.total_amount) if po.total_amount else 0,
            "order_date": str(po.order_date) if po.order_date else None,
            "expected_delivery_date": str(po.expected_delivery_date) if po.expected_delivery_date else None,
        })
    
    if format == "json":
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=purchase_orders_export.json"}
        )
    
    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "PO Number", "Supplier ID", "Status", "Total Amount", "Order Date", "Expected Delivery"])
    for item in data:
        writer.writerow([
            item["id"], item["po_number"], item["supplier_id"], item["status"],
            item["total_amount"], item["order_date"], item["expected_delivery_date"]
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=purchase_orders_export.csv"}
    )


@router.get("/export/expenses")
async def export_expenses(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Export all expenses in the specified format."""
    from src.models.expense import Expense
    
    expenses = db.query(Expense).limit(10000).all()
    
    data = []
    for e in expenses:
        data.append({
            "id": e.id,
            "description": e.description,
            "amount": float(e.amount) if e.amount else 0,
            "category": e.category,
            "expense_date": str(e.expense_date) if e.expense_date else None,
        })
    
    if format == "json":
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=expenses_export.json"}
        )
    
    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Description", "Amount", "Category", "Expense Date"])
    for item in data:
        writer.writerow([item["id"], item["description"], item["amount"], item["category"], item["expense_date"]])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_export.csv"}
    )


@router.get("/export/campaigns")
async def export_campaigns(
    format: Literal["csv", "json"] = Query("csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Export all marketing campaigns in the specified format."""
    from src.models.marketing import MarketingCampaign
    
    campaigns = db.query(MarketingCampaign).limit(10000).all()
    
    data = []
    for c in campaigns:
        data.append({
            "id": c.id,
            "name": c.name,
            "campaign_type": c.campaign_type,
            "status": c.status,
            "start_date": str(c.start_date) if c.start_date else None,
            "end_date": str(c.end_date) if c.end_date else None,
        })
    
    if format == "json":
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=campaigns_export.json"}
        )
    
    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Campaign Type", "Status", "Start Date", "End Date"])
    for item in data:
        writer.writerow([item["id"], item["name"], item["campaign_type"], item["status"], item["start_date"], item["end_date"]])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=campaigns_export.csv"}
    )


# =============================================================================
# Google Sheets Sync Endpoints
# =============================================================================

@router.post("/sheets/sync-pull", response_model=SheetsSyncPullResponse)
async def sheets_sync_pull(
    request: SheetsSyncPullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """
    Pull data from Fulcrum to Google Sheets.
    
    Called by the Apps Script add-on to refresh Sheets data.
    """
    sync_timestamp = datetime.utcnow()
    
    if request.entity == "products":
        products = crud_product.get_multi(db, skip=0, limit=10000)
        data = [
            {
                "id": p.id,
                "sku": p.sku or "",
                "name": p.name,
                "cost_price": p.cost_price or 0,
                "resale_price": p.default_resale_price or 0,
                "stock": sum(i.quantity for i in p.inventory_items) if p.inventory_items else 0,
            }
            for p in products
        ]
    elif request.entity == "inventory":
        products = crud_product.get_multi(db, skip=0, limit=10000)
        data = [
            {
                "product_id": p.id,
                "sku": p.sku or "",
                "name": p.name,
                "stock": sum(i.quantity for i in p.inventory_items) if p.inventory_items else 0,
            }
            for p in products
        ]
    elif request.entity == "suppliers":
        suppliers = crud_supplier.get_multi(db, skip=0, limit=10000)
        data = [
            {"id": s.id, "name": s.name, "email": s.email or "", "phone": s.phone or ""}
            for s in suppliers
        ]
    elif request.entity == "purchase-orders":
        from src.models.purchase_order import PurchaseOrder
        orders = db.query(PurchaseOrder).limit(1000).all()
        data = [
            {
                "id": po.id,
                "po_number": f"PO-{po.id}",
                "supplier_id": po.supplier_id,
                "status": po.status,
                "total_amount": float(po.total_amount) if po.total_amount else 0,
                "date": str(po.ordered_at.date()) if po.ordered_at else str(po.created_at.date()),
            }
            for po in orders
        ]
    elif request.entity == "expenses":
        from src.models.expense import Expense
        expenses = db.query(Expense).limit(1000).all()
        data = [
            {
                "id": e.id,
                "description": e.description,
                "amount": float(e.amount) if e.amount else 0,
                "category": e.category,
                "date": str(e.date) if e.date else "",
            }
            for e in expenses
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entity: {request.entity}")
    
    return SheetsSyncPullResponse(
        data=data,
        sync_timestamp=sync_timestamp,
        total_records=len(data)
    )

@router.post("/sheets/sync-push", response_model=SheetsSyncPushResponse)
async def sheets_sync_push(
    request: SheetsSyncPushRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """
    Push changes from Google Sheets back to Fulcrum.
    
    IMPORTANT: Changes are STAGED for review, not applied immediately.
    The user must approve changes in the Fulcrum app before they take effect.
    
    Called by the Apps Script add-on when user edits data in Sheets.
    """
    errors = []
    staged_count = 0
    
    allowed_fields = {"stock", "cost_price", "resale_price", "name"}
    
    # Create a new SyncBatch to group these changes
    batch = SyncBatch(
        user_id=current_user.id,
        source="google_sheets",
        status="pending",
        total_changes=0,  # Will update after processing
    )
    db.add(batch)
    db.flush()  # Get batch ID
    
    for change in request.changes:
        try:
            product_id = change.get("id")
            field = change.get("field")
            new_value = change.get("new_value")
            
            if not product_id or not field:
                errors.append(f"Invalid change record: {change}")
                continue
            
            if field not in allowed_fields:
                errors.append(f"Field '{field}' is not allowed for sync")
                continue
            
            product = crud_product.get(db, id=product_id)
            if not product:
                errors.append(f"Product {product_id} not found")
                continue
            
            # Get current value for preview
            if field == "cost_price":
                old_value = str(product.cost_price) if product.cost_price else "0"
            elif field == "resale_price":
                old_value = str(product.default_resale_price) if product.default_resale_price else "0"
            elif field == "name":
                old_value = product.name or ""
            elif field == "stock":
                old_value = str(sum(i.quantity for i in product.inventory_items) if product.inventory_items else 0)
            else:
                old_value = None
            
            # CHECK: If value hasn't changed, skip it
            # Normalize to strings for comparison
            normalized_new = str(new_value).strip() if new_value is not None else ""
            normalized_old = str(old_value).strip() if old_value is not None else ""
            
            # Floating point comparison for prices
            if field in ["cost_price", "resale_price"]:
                try:
                    float_new = float(normalized_new)
                    float_old = float(normalized_old) if normalized_old else 0.0
                    if abs(float_new - float_old) < 0.001:
                        continue
                except ValueError:
                    # Parse error, fallback to string compare
                    if normalized_new == normalized_old:
                        continue
            else:
                if normalized_new == normalized_old:
                    continue

            
            # Create pending change record
            pending_change = PendingSyncChange(
                batch_id=batch.id,
                entity=request.entity,
                entity_id=product_id,
                entity_name=product.name,
                entity_sku=product.sku,
                field=field,
                old_value=old_value,
                new_value=str(new_value),
                status="pending",
            )
            db.add(pending_change)
            staged_count += 1
                
        except Exception as e:
            errors.append(f"Error processing change: {str(e)}")
    
    # Update batch with total count
    batch.total_changes = staged_count
    db.commit()
    
    return SheetsSyncPushResponse(
        success=staged_count > 0,
        batch_id=batch.id,
        staged_count=staged_count,
        message=f"{staged_count} changes staged for review. Open Fulcrum → Settings → Integrations & Data to approve.",
        errors=errors
    )


@router.get("/sync/pending", response_model=PendingBatchListResponse)
async def list_pending_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    List all pending sync batches with their changes for review.
    """
    batches = db.query(SyncBatch).filter(
        SyncBatch.status == "pending"
    ).order_by(SyncBatch.created_at.desc()).all()

    batch_ids = [batch.id for batch in batches]
    changes_by_batch: dict[int, list[PendingSyncChange]] = defaultdict(list)
    if batch_ids:
        pending_changes = db.query(PendingSyncChange).filter(
            PendingSyncChange.batch_id.in_(batch_ids),
            PendingSyncChange.status == "pending",
        ).all()
        for change in pending_changes:
            changes_by_batch[change.batch_id].append(change)

    batch_list = []
    total_pending = 0
    
    for batch in batches:
        changes = changes_by_batch[batch.id]

        batch_info = PendingBatchInfo(
            id=batch.id,
            source=batch.source,
            status=batch.status,
            total_changes=batch.total_changes,
            approved_count=batch.approved_count,
            rejected_count=batch.rejected_count,
            created_at=batch.created_at,
            changes=[
                PendingChangeInfo(
                    id=c.id,
                    entity_id=c.entity_id,
                    entity_name=c.entity_name,
                    entity_sku=c.entity_sku,
                    field=c.field,
                    old_value=c.old_value,
                    new_value=c.new_value,
                    status=c.status,
                )
                for c in changes
            ]
        )
        batch_list.append(batch_info)
        total_pending += len(changes)
    
    return PendingBatchListResponse(
        batches=batch_list,
        total_pending=total_pending
    )


@router.get("/sync/pending/count")
async def get_pending_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Get count of pending changes and batches (for badge display)."""
    change_count = db.query(PendingSyncChange).filter(
        PendingSyncChange.status == "pending"
    ).count()
    
    batch_count = db.query(SyncBatch).filter(
        SyncBatch.status == "pending"
    ).count()
    
    return {"count": change_count, "batch_count": batch_count}


@router.post("/sync/approve", response_model=SyncApproveResponse)
async def approve_sync_changes(
    request: SyncApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    Approve or reject specific pending sync changes.
    
    When approved, changes are applied to the database and logged to EntityChangeLog.
    """
    errors = []
    applied_count = 0
    
    batch = db.query(SyncBatch).filter(SyncBatch.id == request.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    for change_id in request.change_ids:
        change = db.query(PendingSyncChange).filter(
            PendingSyncChange.id == change_id,
            PendingSyncChange.batch_id == request.batch_id
        ).first()
        
        if not change:
            errors.append(f"Change {change_id} not found in batch")
            continue
        
        if request.action == "approve":
            # Apply the change
            try:
                product = crud_product.get(db, id=change.entity_id)
                if not product:
                    errors.append(f"Product {change.entity_id} not found")
                    continue
                
                # Apply update based on field
                if change.field == "cost_price":
                    crud_product.update(db, db_obj=product, obj_in={"cost_price": float(change.new_value)})
                elif change.field == "resale_price":
                    crud_product.update(db, db_obj=product, obj_in={"default_resale_price": float(change.new_value)})
                elif change.field == "name":
                    crud_product.update(db, db_obj=product, obj_in={"name": change.new_value})
                elif change.field == "stock":
                    # Stock changes are complex - for now, log but don't apply
                    errors.append(f"Stock sync for {change.entity_name} requires manual adjustment")
                    continue
                
                # Log the change with source attribution
                log_entry = EntityChangeLog(
                    entity_type="product",
                    entity_id=change.entity_id,
                    entity_name=change.entity_name,
                    field=change.field,
                    old_value=change.old_value,
                    new_value=change.new_value,
                    source="sheets_import",
                    source_batch_id=batch.id,
                    changed_by_id=current_user.id,
                )
                db.add(log_entry)
                
                change.status = "approved"
                batch.approved_count += 1
                applied_count += 1
                
            except Exception as e:
                errors.append(f"Error applying change {change_id}: {str(e)}")
                
        elif request.action == "reject":
            change.status = "rejected"
            batch.rejected_count += 1
    
    # Update batch status
    pending_count = db.query(PendingSyncChange).filter(
        PendingSyncChange.batch_id == batch.id,
        PendingSyncChange.status == "pending"
    ).count()
    
    if pending_count == 0:
        if batch.rejected_count == batch.total_changes:
            batch.status = "rejected"
        elif batch.approved_count == batch.total_changes:
            batch.status = "approved"
        else:
            batch.status = "partial"
        batch.reviewed_at = datetime.utcnow()
        batch.reviewed_by_id = current_user.id
        
        # Clean up pending changes after batch is fully processed
        db.query(PendingSyncChange).filter(
            PendingSyncChange.batch_id == batch.id
        ).delete()
    
    db.commit()
    
    action_label = "approved" if request.action == "approve" else "rejected"
    return SyncApproveResponse(
        success=len(errors) == 0,
        applied_count=applied_count if request.action == "approve" else len(request.change_ids) - len(errors),
        message=f"{applied_count} changes {action_label}." if request.action == "approve" else f"{len(request.change_ids)} changes rejected.",
        errors=errors
    )


@router.get("/change-logs", response_model=ChangeLogResponse)
async def list_change_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    List entity change logs with optional filters.
    
    Use this to see the audit trail of all changes, including source attribution.
    """
    query = db.query(EntityChangeLog)
    
    if entity_type:
        query = query.filter(EntityChangeLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(EntityChangeLog.entity_id == entity_id)
    if source:
        query = query.filter(EntityChangeLog.source == source)
    
    total = query.count()
    entries = query.order_by(EntityChangeLog.changed_at.desc()).offset(offset).limit(limit).all()
    
    return ChangeLogResponse(
        entries=[
            ChangeLogEntry(
                id=e.id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                entity_name=e.entity_name,
                field=e.field,
                old_value=e.old_value,
                new_value=e.new_value,
                source=e.source,
                changed_by_email=e.changed_by.email if e.changed_by else None,
                changed_at=e.changed_at,
            )
            for e in entries
        ],
        total=total
    )


# =============================================================================
# API Key Management Endpoints
# =============================================================================

class ApiKeyCreateRequest(BaseModel):
    """Request to create a new API key."""
    name: str  # e.g., "Google Sheets Integration"


class ApiKeyCreateResponse(BaseModel):
    """Response with the newly created API key (shown only once!)."""
    id: int
    name: str
    key_prefix: str
    api_key: str  # Full key - only shown at creation time!
    created_at: datetime


class ApiKeyInfo(BaseModel):
    """Public info about an API key (does not include the actual key)."""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    Generate a new API key for external tool authentication.
    
    The full API key is returned ONLY in this response. Store it securely!
    """
    # Generate a secure random key (32 bytes = 64 hex chars)
    raw_key = secrets.token_hex(32)
    key_prefix = raw_key[:8]
    
    # Hash the key for storage (we'll use a simple SHA256 for API keys)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # Create the API key record
    api_key = ApiKey(
        user_id=current_user.id,
        name=request.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=raw_key,  # Only time the full key is returned!
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=List[ApiKeyInfo])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """List all API keys for the current user."""
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    return [
        ApiKeyInfo(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_user),
):
    """Revoke (deactivate) an API key."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}


# =============================================================================
# API Key Authentication Dependency (for Apps Script)
# =============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Validate an API key and return the associated user.
    Returns None if no API key provided (allows fallback to JWT).
    """
    if not api_key:
        return None
    
    # Hash the provided key to compare
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Find matching active key
    db_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active
    ).first()
    
    if not db_key:
        return None
    
    # Update last used timestamp
    db_key.last_used_at = datetime.utcnow()
    db.commit()
    
    # Return the user
    return db.query(User).filter(User.id == db_key.user_id).first()
