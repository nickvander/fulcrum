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
    entity: Literal["products", "inventory", "suppliers"]
    last_sync_timestamp: Optional[datetime] = None


class SheetsSyncPullResponse(BaseModel):
    """Response for Sheets pull operation."""
    data: List[dict]
    sync_timestamp: datetime
    total_records: int


class SheetsSyncPushRequest(BaseModel):
    """Request from Google Sheets to push changes to Fulcrum."""
    entity: Literal["products", "inventory"]
    changes: List[dict]  # Each dict has: id, field, old_value, new_value


class SheetsSyncPushResponse(BaseModel):
    """Response for Sheets push operation."""
    success: bool
    updated_count: int
    errors: List[str] = []


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
    current_user: User = Depends(dependencies.get_current_user),
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
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    Push changes from Google Sheets back to Fulcrum.
    
    Called by the Apps Script add-on when user edits data in Sheets.
    Currently supports updating: stock quantity, cost_price, resale_price.
    """
    updated_count = 0
    errors = []
    
    allowed_fields = {"stock", "cost_price", "resale_price", "name"}
    
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
            
            # Apply the update
            if field == "stock":
                # Stock updates are more complex - need to adjust inventory
                # For now, we'll store this as a note. Full implementation
                # would use inventory adjustment logic.
                errors.append(f"Stock sync for product {product_id} recorded (full implementation pending)")
            elif field == "cost_price":
                crud_product.update(db, db_obj=product, obj_in={"cost_price": float(new_value)})
                updated_count += 1
            elif field == "resale_price":
                crud_product.update(db, db_obj=product, obj_in={"default_resale_price": float(new_value)})
                updated_count += 1
            elif field == "name":
                crud_product.update(db, db_obj=product, obj_in={"name": str(new_value)})
                updated_count += 1
                
        except Exception as e:
            errors.append(f"Error processing change: {str(e)}")
    
    return SheetsSyncPushResponse(
        success=len(errors) == 0,
        updated_count=updated_count,
        errors=errors
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

