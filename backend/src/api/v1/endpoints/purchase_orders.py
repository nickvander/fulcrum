from typing import List, Any
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel

from src.database import get_db
from src.crud import crud_purchase_order
from src.crud.crud_supplier_invoice import supplier_invoice as crud_supplier_invoice
from src.schemas import purchase_order as po_schema
from src.schemas import supplier_invoice as invoice_schema
from src.services.purchase_order_service import purchase_order_service
from src.api.dependencies import get_current_active_user
from src.models.user import User

router = APIRouter()


# --- Cost Allocation Schemas ---
class CostAllocationPreviewItem(BaseModel):
    """Preview of how costs will be allocated to a single item."""
    item_id: int
    product_name: str
    quantity: float
    current_unit_cost: float
    base_cost: float
    shipping_to_add: float
    taxes_to_add: float
    other_to_add: float
    new_unit_cost: float


class CostAllocationPreview(BaseModel):
    """Preview of cost allocation for the entire PO."""
    po_id: int
    total_shipping: float
    total_taxes: float
    total_other: float
    total_quantity: float
    per_unit_shipping: float
    per_unit_taxes: float
    per_unit_other: float
    items: List[CostAllocationPreviewItem]


class ApplyCostsRequest(BaseModel):
    """Request to apply costs to PO items."""
    confirm: bool = True  # Must be True to apply
    excluded_items: List[int] = []  # IDs of items to exclude from allocation


@router.post("/", response_model=po_schema.PurchaseOrder)
def create_purchase_order(
    *,
    db: Session = Depends(get_db),
    po_in: po_schema.PurchaseOrderCreate,
) -> Any:
    """
    Create a new Purchase Order.
    """
    po = crud_purchase_order.purchase_order.create_with_items(db=db, obj_in=po_in)
    
    # Calculate landed costs if any are present
    if po.shipping_cost or po.tax_amount or po.other_costs:
        po = purchase_order_service.calculate_landed_costs(db=db, po_id=po.id)
        
    return po

@router.get("/", response_model=List[po_schema.PurchaseOrder])
def read_purchase_orders(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve Purchase Orders.
    """
    return crud_purchase_order.purchase_order.get_multi(db, skip=skip, limit=limit)

@router.get("/{id}", response_model=po_schema.PurchaseOrder)
def read_purchase_order(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get Purchase Order by ID.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return po

@router.put("/{id}", response_model=po_schema.PurchaseOrder)
def update_purchase_order(
    *,
    db: Session = Depends(get_db),
    id: int,
    po_in: po_schema.PurchaseOrderUpdate,
) -> Any:
    """
    Update a Purchase Order.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    po = crud_purchase_order.purchase_order.update(db=db, db_obj=po, obj_in=po_in)
    
    # Recalculate landed costs if cost fields were modified
    if (po_in.shipping_cost is not None or 
        po_in.tax_amount is not None or 
        po_in.other_costs is not None):
        po = purchase_order_service.calculate_landed_costs(db=db, po_id=po.id)
        
    return po

@router.post("/{id}/status", response_model=po_schema.PurchaseOrder)
def transition_status(
    *,
    db: Session = Depends(get_db),
    id: int,
    status: po_schema.PurchaseOrderStatus,
):
    """
    Transition Purchase Order status.
    """
    try:
        po = purchase_order_service.transition_status(db=db, po_id=id, new_status=status)
        return po
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/receive", response_model=po_schema.PurchaseOrder)
def receive_items(
    *,
    db: Session = Depends(get_db),
    id: int,

    received_items: List[dict],  # Ideally define a schema for this
    current_user: User = Depends(get_current_active_user),
):
    """
    Receive items for a Purchase Order.
    Body: List of { "product_id": int, "quantity": int }
    """
    try:
        po = purchase_order_service.receive_items(db=db, po_id=id, received_items=received_items, user=current_user)
        return po
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_model=po_schema.PurchaseOrder)
def delete_purchase_order(
    *,
    db: Session = Depends(get_db),
    id: int,
):
    """
    Delete a Purchase Order.
    Safety: Cannot delete if any items have been received.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Safety Check: Prevent deletion if any stock has been received
    # This prevents orphaned inventory records ("ghost stock")
    has_received_items = any((item.quantity_received or 0) > 0 for item in po.items)
    
    if has_received_items:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete Purchase Order because items have already been received. "
                   "To reverse this, please manually adjust stock and mark the PO as Closed."
        )

    po = crud_purchase_order.purchase_order.remove(db=db, id=id)
    return po


@router.get("/{id}/costs/preview", response_model=CostAllocationPreview)
def preview_cost_allocation(
    *,
    db: Session = Depends(get_db),
    id: int,
    excluded_items: List[int] = Query([], alias="excluded_items"),  # Use Query for list
    shipping_cost: float = None,
    tax_amount: float = None,
    other_costs: float = None,
):
    """
    Preview how additional costs (shipping, taxes, other) will be allocated
    across PO line items. Returns itemized breakdown before applying.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Use provided values or fallback to DB values
    # Treating explicit 0 as override (check for None)
    c_shipping = shipping_cost if shipping_cost is not None else (po.shipping_cost or 0)
    c_tax = tax_amount if tax_amount is not None else (po.tax_amount or 0)
    c_other = other_costs if other_costs is not None else (po.other_costs or 0)

    # Calculate total quantity across all items (excluding ignored ones)
    allocatable_items = [item for item in po.items if item.id not in excluded_items]
    total_qty = sum(item.quantity_ordered for item in allocatable_items)
    
    # Calculate per-unit costs (handled gracefully if no items)
    if total_qty > 0:
        per_unit_shipping = c_shipping / total_qty
        per_unit_taxes = c_tax / total_qty
        per_unit_other = c_other / total_qty
    else:
        per_unit_shipping = 0
        per_unit_taxes = 0
        per_unit_other = 0
    
    # Build preview for each item
    preview_items = []
    for item in po.items:
        product_name = item.product.name if item.product else f"Product #{item.product_id}"
        
        # Use existing base_cost if set, otherwise use current unit_cost
        base = item.base_cost if item.base_cost > 0 else item.unit_cost
        
        if item.id in excluded_items:
             preview_items.append(CostAllocationPreviewItem(
                item_id=item.id,
                product_name=product_name,
                quantity=item.quantity_ordered,
                current_unit_cost=item.unit_cost,
                base_cost=base,
                shipping_to_add=0,
                taxes_to_add=0,
                other_to_add=0,
                new_unit_cost=base,
            ))
        else:
            preview_items.append(CostAllocationPreviewItem(
                item_id=item.id,
                product_name=product_name,
                quantity=item.quantity_ordered,
                current_unit_cost=item.unit_cost,
                base_cost=base,
                shipping_to_add=per_unit_shipping,
                taxes_to_add=per_unit_taxes,
                other_to_add=per_unit_other,
                new_unit_cost=base + per_unit_shipping + per_unit_taxes + per_unit_other,
            ))
    
    return CostAllocationPreview(
        po_id=po.id,
        total_shipping=c_shipping,
        total_taxes=c_tax,
        total_other=c_other,
        total_quantity=total_qty,
        per_unit_shipping=per_unit_shipping,
        per_unit_taxes=per_unit_taxes,
        per_unit_other=per_unit_other,
        items=preview_items,
    )


@router.post("/{id}/costs/apply", response_model=po_schema.PurchaseOrder)
def apply_cost_allocation(
    *,
    db: Session = Depends(get_db),
    id: int,
    request: ApplyCostsRequest,
):
    """
    Apply additional costs to PO line items.
    Distributes shipping, taxes, and other costs evenly per unit.
    Records the breakdown for future reference.
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Must confirm=True to apply costs")
    
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Calculate total quantity (excluding ignored)
    excluded_ids = request.excluded_items
    allocatable_items = [item for item in po.items if item.id not in excluded_ids]
    total_qty = sum(item.quantity_ordered for item in allocatable_items)
    
    if total_qty > 0:
        per_unit_shipping = (po.shipping_cost or 0) / total_qty
        per_unit_taxes = (po.tax_amount or 0) / total_qty
        per_unit_other = (po.other_costs or 0) / total_qty
    else:
        # If everything is excluded, or 0 qty, no costs applied
        per_unit_shipping = 0
        per_unit_taxes = 0
        per_unit_other = 0
    
    # Apply to each item
    now = datetime.now(timezone.utc)
    for item in po.items:
        # Set base_cost from current unit_cost if not already set
        if item.base_cost == 0:
            item.base_cost = item.unit_cost
            
        if item.id in excluded_ids:
            # Reset allocations for excluded items
            item.shipping_allocated = 0
            item.taxes_allocated = 0
            item.other_allocated = 0
            item.unit_cost = item.base_cost # Revert to base
        else:
            # Record allocated amounts
            item.shipping_allocated = per_unit_shipping
            item.taxes_allocated = per_unit_taxes
            item.other_allocated = per_unit_other
            item.unit_cost = item.base_cost + per_unit_shipping + per_unit_taxes + per_unit_other
            
        item.costs_applied_at = now
    
    db.commit()
    db.refresh(po)
    return po


# --- Invoice Management Endpoints ---
# Security: Allowed file types and max size
ALLOWED_INVOICE_TYPES = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_INVOICE_SIZE = 10 * 1024 * 1024  # 10MB
INVOICE_UPLOAD_DIR = "uploads/invoices"


@router.post("/{id}/invoices", response_model=invoice_schema.SupplierInvoice)
async def upload_invoice(
    *,
    db: Session = Depends(get_db),
    id: int,
    file: UploadFile = File(...),
    invoice_number: str = None,
):
    """
    Upload an invoice file for a Purchase Order.
    
    Security:
    - Only PDF, PNG, JPG, JPEG files allowed
    - Max file size: 10MB
    - Files renamed to UUID to prevent path traversal
    """
    # Verify PO exists
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Validate file type
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_INVOICE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_INVOICE_TYPES)}"
        )
    
    # Read file and check size
    content = await file.read()
    if len(content) > MAX_INVOICE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Maximum size: {MAX_INVOICE_SIZE // (1024*1024)}MB"
        )
    
    # Create secure filename with UUID
    secure_filename = f"{uuid.uuid4().hex}{file_ext}"
    po_dir = f"{INVOICE_UPLOAD_DIR}/{id}"
    os.makedirs(po_dir, exist_ok=True)
    
    file_path = f"{po_dir}/{secure_filename}"
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create invoice record
    invoice_in = invoice_schema.SupplierInvoiceCreate(
        po_id=id,
        invoice_number=invoice_number,
        file_path=file_path,
    )
    invoice = crud_supplier_invoice.create(db=db, obj_in=invoice_in)
    
    return invoice


@router.get("/{id}/invoices", response_model=List[invoice_schema.SupplierInvoice])
def list_invoices(
    *,
    db: Session = Depends(get_db),
    id: int,
):
    """
    List all invoices attached to a Purchase Order.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    return crud_supplier_invoice.get_by_po(db=db, po_id=id)


@router.delete("/invoices/{invoice_id}")
def delete_invoice(
    *,
    db: Session = Depends(get_db),
    invoice_id: int,
):
    """
    Delete an invoice and its associated file.
    """
    invoice = crud_supplier_invoice.get(db=db, id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Delete file if exists
    if invoice.file_path and os.path.exists(invoice.file_path):
        try:
            os.remove(invoice.file_path)
        except OSError:
            pass  # File already deleted or inaccessible
    
    crud_supplier_invoice.remove(db=db, id=invoice_id)
    
    return {"message": "Invoice deleted successfully"}
