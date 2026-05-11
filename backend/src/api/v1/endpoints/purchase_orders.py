from typing import List, Any, Optional
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
from src.models.supplier import Supplier
from src.models.supplier_document_import import SupplierDocumentImport

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


class ReceiveItemRequest(BaseModel):
    """A line item quantity to receive into inventory."""
    po_item_id: Optional[int] = None
    product_id: int
    variant_id: Optional[int] = None
    quantity: float


class ReceiveCorrectionRequest(BaseModel):
    """A received quantity to reverse from a purchase order line."""
    po_item_id: Optional[int] = None
    product_id: int
    variant_id: Optional[int] = None
    quantity: float
    reason: Optional[str] = None


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
    received_items: List[ReceiveItemRequest],
    current_user: User = Depends(get_current_active_user),
):
    """
    Receive items for a Purchase Order.
    Body: List of { "po_item_id"?: int, "product_id": int, "variant_id"?: int, "quantity": number }
    """
    try:
        po = purchase_order_service.receive_items(db=db, po_id=id, received_items=received_items, user=current_user)
        return po
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/receive-correction", response_model=po_schema.PurchaseOrder)
def correct_received_items(
    *,
    db: Session = Depends(get_db),
    id: int,
    corrections: List[ReceiveCorrectionRequest],
    current_user: User = Depends(get_current_active_user),
):
    """
    Reverse receiving mistakes for a Purchase Order.
    Body: List of { "po_item_id"?: int, "product_id": int, "variant_id"?: int, "quantity": number, "reason"?: string }
    """
    try:
        po = purchase_order_service.correct_received_items(
            db=db, po_id=id, corrections=corrections, user=current_user
        )
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
ALLOWED_INVOICE_TYPES = {'.pdf', '.png', '.jpg', '.jpeg', '.avif'}
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

# --- Unified Document Parse Schemas ---
class ExtractedItem(BaseModel):
    """An extracted line item from a document."""
    sku: str | None = None
    description: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    line_total: float = 0.0
    matched_product_id: int | None = None
    matched_variant_id: int | None = None


class DocumentParseResult(BaseModel):
    """
    Unified result from parsing a supplier document.
    
    mode:
    - "create": No matching PO found, use data to create new PO
    - "match": Found matching PO, shows comparison for reconciliation
    """
    mode: str  # "create" or "match"
    
    # Extracted document data
    vendor_name: str | None = None
    po_number: str | None = None
    invoice_number: str | None = None
    document_date: str | None = None
    currency: str = "USD"
    items: List[ExtractedItem] = []
    subtotal: float = 0.0
    shipping_cost: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    confidence: float = 0.0
    
    # If mode == "match"
    matched_po_id: int | None = None
    matched_po_number: str | None = None
    matched_supplier_name: str | None = None
    match_confidence: float = 0.0
    matches: List[Any] = []  # InvoiceMatchItem objects
    unmatched_po_items: List[dict] = []
    unmatched_invoice_items: List[dict] = []
    total_discrepancy: float = 0.0


class SupplierDocumentImportRead(BaseModel):
    id: int
    file_name: str
    content_type: str | None = None
    source: str | None = None
    status: str
    mode: str
    supplier_id: int | None = None
    purchase_order_id: int | None = None
    extracted_data: dict
    warnings: List[str] = []
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SupplierDocumentImportApproveRequest(BaseModel):
    supplier_id: int
    currency: str = "USD"
    shipping_cost: float = 0.0
    tax_amount: float = 0.0
    notes: str | None = None
    items: List[ExtractedItem]


class SupplierDocumentImportApproveResponse(BaseModel):
    import_review: SupplierDocumentImportRead
    purchase_order: po_schema.PurchaseOrder


def _import_review_response(review: SupplierDocumentImport) -> SupplierDocumentImportRead:
    return SupplierDocumentImportRead(
        id=review.id,
        file_name=review.file_name,
        content_type=review.content_type,
        source=review.source,
        status=review.status,
        mode=review.mode,
        supplier_id=review.supplier_id,
        purchase_order_id=review.purchase_order_id,
        extracted_data=review.extracted_data or {},
        warnings=review.warnings or [],
        created_at=review.created_at,
        reviewed_at=review.reviewed_at,
    )


def _find_supplier_id_for_vendor(db: Session, vendor_name: str | None) -> int | None:
    if not vendor_name:
        return None

    vendor_lower = vendor_name.lower()
    suppliers = db.query(Supplier).limit(500).all()
    for supplier in suppliers:
        supplier_lower = supplier.name.lower()
        if vendor_lower in supplier_lower or supplier_lower in vendor_lower:
            return supplier.id
    return None


@router.post("/imports/reviews", response_model=SupplierDocumentImportRead)
async def create_supplier_document_import_review(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    target_po_id: int | None = Query(None, description="Optional: PO ID to match against"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Parse a supplier document and stage it for review before creating a PO or stock movement.
    """
    result = await parse_document(db=db, file=file, target_po_id=target_po_id)
    extracted_data = result.model_dump(mode="json")
    warnings = []

    if result.mode == "match":
        warnings.append("This document appears to match an existing PO. Review it there before receiving stock.")

    unmatched_items = [
        item for item in result.items
        if not item.matched_product_id
    ]
    if unmatched_items:
        warnings.append(f"{len(unmatched_items)} line item(s) need a Fulcrum product match before approval.")

    review = SupplierDocumentImport(
        file_name=file.filename or "supplier-document",
        content_type=file.content_type,
        status="pending",
        mode=result.mode,
        supplier_id=_find_supplier_id_for_vendor(db, result.vendor_name),
        purchase_order_id=result.matched_po_id,
        extracted_data=extracted_data,
        warnings=warnings,
        created_by_id=current_user.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _import_review_response(review)


@router.get("/imports/reviews", response_model=List[SupplierDocumentImportRead])
def list_supplier_document_import_reviews(
    *,
    db: Session = Depends(get_db),
    status: str | None = Query("pending"),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(SupplierDocumentImport).order_by(
        SupplierDocumentImport.created_at.desc(),
        SupplierDocumentImport.id.desc(),
    )
    if status:
        query = query.filter(SupplierDocumentImport.status == status)
    return [_import_review_response(review) for review in query.limit(100).all()]


@router.get("/imports/reviews/{review_id}", response_model=SupplierDocumentImportRead)
def get_supplier_document_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    current_user: User = Depends(get_current_active_user),
):
    review = db.query(SupplierDocumentImport).filter(SupplierDocumentImport.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Import review not found")
    return _import_review_response(review)


@router.post("/imports/reviews/{review_id}/approve", response_model=SupplierDocumentImportApproveResponse)
def approve_supplier_document_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    approval: SupplierDocumentImportApproveRequest,
    current_user: User = Depends(get_current_active_user),
):
    review = db.query(SupplierDocumentImport).filter(SupplierDocumentImport.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Import review not found")
    if review.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending import reviews can be approved")

    matched_items = [
        item for item in approval.items
        if item.quantity > 0 and item.matched_product_id
    ]
    if not matched_items:
        raise HTTPException(status_code=400, detail="At least one reviewed line item must be matched to a product")

    po_in = po_schema.PurchaseOrderCreate(
        supplier_id=approval.supplier_id,
        status=po_schema.PurchaseOrderStatus.DRAFT,
        currency=approval.currency,
        shipping_cost=approval.shipping_cost,
        tax_amount=approval.tax_amount,
        notes=approval.notes or f"Created from supplier import review #{review.id}: {review.file_name}",
        items=[
            po_schema.PurchaseOrderItemCreate(
                product_id=item.matched_product_id,
                variant_id=item.matched_variant_id,
                quantity_ordered=item.quantity,
                unit_cost=item.unit_cost,
                supplier_sku=item.sku,
                supplier_product_name=item.description or item.sku,
            )
            for item in matched_items
        ],
    )
    po = crud_purchase_order.purchase_order.create_with_items(db=db, obj_in=po_in)

    review.status = "approved"
    review.supplier_id = approval.supplier_id
    review.purchase_order_id = po.id
    review.reviewed_by_id = current_user.id
    review.reviewed_at = datetime.now(timezone.utc)
    db.add(review)
    db.commit()
    db.refresh(review)
    po = crud_purchase_order.purchase_order.get(db=db, id=po.id)

    return SupplierDocumentImportApproveResponse(
        import_review=_import_review_response(review),
        purchase_order=po,
    )


@router.post("/imports/reviews/{review_id}/reject", response_model=SupplierDocumentImportRead)
def reject_supplier_document_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    current_user: User = Depends(get_current_active_user),
):
    review = db.query(SupplierDocumentImport).filter(SupplierDocumentImport.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Import review not found")
    if review.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending import reviews can be rejected")

    review.status = "rejected"
    review.reviewed_by_id = current_user.id
    review.reviewed_at = datetime.now(timezone.utc)
    db.add(review)
    db.commit()
    db.refresh(review)
    return _import_review_response(review)


@router.post("/parse-document", response_model=DocumentParseResult)
async def parse_document(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    target_po_id: int | None = Query(None, description="Optional: PO ID to match against"),
):
    """
    Unified endpoint to parse supplier documents (invoices, quotes, POs).
    
    Smart behavior:
    - If target_po_id provided: Match against that specific PO
    - Otherwise: Search for matching PO by PO number or vendor+items
    - If match found: Return mode="match" with comparison data
    - If no match: Return mode="create" with extracted data
    """
    from difflib import SequenceMatcher
    from src.services.adk.manager import ADKManager
    from src.services.adk.orchestrator import AgentOrchestrator
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    
    # Validate file type
    allowed_types = {'.pdf', '.png', '.jpg', '.jpeg', '.avif', '.html', '.htm', '.txt'}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
    
    # Determine MIME type
    mime_map = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.avif': 'image/avif',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.txt': 'text/plain'
    }
    mime_type = mime_map.get(file_ext, 'text/plain')
    
    from src.services.purchase_order_ingestion_service import po_ingestion_service
    
    # Get store settings for AI config
    settings = crud_store_settings.get_settings(db)
    ai_enabled = settings.ai_enabled if settings else False
    
    extraction_result = {}
    
    # 1. Try traditional parsing first for text-based documents (PDF, HTML, TXT)
    if file_ext in ('.pdf', '.html', '.htm', '.txt'):
        try:
            traditional_data = po_ingestion_service.ingest_file(file.filename, content)
            # If we got meaningful data (especially items), use it
            has_traditional_data = (
                bool(traditional_data.items)
                or bool(traditional_data.supplier_name)
                or traditional_data.total_amount > 0
            )
            if has_traditional_data:
                extraction_result = {
                    "vendor_name": traditional_data.supplier_name,
                    "po_number": traditional_data.po_number,
                    "invoice_number": traditional_data.po_number,
                    "invoice_date": traditional_data.po_date.strftime("%Y-%m-%d") if traditional_data.po_date else None,
                    "currency": traditional_data.currency,
                    "items": [
                        {
                            "sku": item.sku,
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit_cost": item.unit_cost,
                            "line_total": item.line_total
                        } for item in traditional_data.items
                    ],
                    "subtotal": traditional_data.subtotal,
                    "shipping_cost": traditional_data.shipping_cost,
                    "tax_amount": traditional_data.tax_amount,
                    "total_amount": traditional_data.total_amount,
                    "confidence": traditional_data.confidence_score,
                    "extraction_method": traditional_data.extraction_method
                }
        except Exception as e:
            print(f"[parse_document] Traditional parsing failed: {e}")
            if not ai_enabled:
                raise HTTPException(status_code=500, detail=f"Traditional parsing failed: {str(e)}")
    
    # 2. Use AI if traditional parsing failed/low confidence AND AI is enabled
    # Also use AI for images (AVIF, PNG, JPG)
    if (not extraction_result or extraction_result.get("confidence", 0) < 0.6) and ai_enabled:
        # Initialize ADK manager and orchestrator
        adk_manager = ADKManager(db)
        orchestrator = AgentOrchestrator(adk_manager)
        
        # Parse document using AI
        ai_result = await orchestrator.parse_invoice(content, mime_type)
        
        if "error" not in ai_result:
            # If AI result is better (higher confidence or more items), merge/use it
            if not extraction_result or ai_result.get("confidence", 0) > extraction_result.get("confidence", 0):
                extraction_result = ai_result
                extraction_result["extraction_method"] = "ai"
        elif not extraction_result:
             raise HTTPException(status_code=500, detail=ai_result["error"])
    
    if not extraction_result:
        raise HTTPException(
            status_code=400, 
            detail="Could not extract readable order data. Text PDFs/HTML can be parsed without AI; scanned PDFs and images need AI/OCR enabled in Settings."
        )
    
    # Extract document data
    extracted_items = extraction_result.get("items", []) or extraction_result.get("line_items", [])
    extraction_confidence = extraction_result.get("confidence", 0.5)
    doc_po_number = extraction_result.get("po_number") or extraction_result.get("invoice_number")
    doc_vendor = extraction_result.get("vendor_name")
    
    # Convert to ExtractedItem list
    items = [
        ExtractedItem(
            sku=item.get("sku"),
            description=item.get("description", ""),
            quantity=item.get("quantity", 0),
            unit_cost=item.get("unit_cost", 0),
            line_total=item.get("line_total", 0)
        )
        for item in extracted_items
    ]
    
    # Helper function for string similarity
    def similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    # === SMART PO MATCHING ===
    matched_po = None
    match_confidence = 0.0
    
    # 1. If target_po_id specified, use that PO
    if target_po_id:
        matched_po = crud_purchase_order.purchase_order.get(db=db, id=target_po_id)
        if matched_po:
            match_confidence = 1.0  # User explicitly requested this PO
    
    # 2. Otherwise, search for matching PO
    if not matched_po:
        all_pos = crud_purchase_order.purchase_order.get_multi(db=db, limit=500)
        
        for po in all_pos:
            po_score = 0.0
            
            # Check vendor match (primary matching criteria since model has no po_number)
            if doc_vendor and po.supplier:
                vendor_sim = similarity(doc_vendor, po.supplier.name)
                if vendor_sim > 0.7:
                    po_score = vendor_sim * 0.6
            
            # If good PO match, check item overlap
            if po_score > 0.5 and po.items:
                item_matches = 0
                for item in items:
                    for po_item in po.items:
                        if not po_item.product:
                            continue
                        # SKU match
                        if item.sku and po_item.product.sku:
                            if item.sku.upper() == po_item.product.sku.upper():
                                item_matches += 1
                                break
                        # Description similarity
                        if similarity(item.description, po_item.product.name or "") > 0.6:
                            item_matches += 1
                            break
                
                if items and item_matches > 0:
                    item_ratio = item_matches / len(items)
                    po_score = po_score * 0.5 + item_ratio * 0.5
            
            if po_score > match_confidence and po_score > 0.5:
                match_confidence = po_score
                matched_po = po
    
    # === BUILD RESPONSE ===
    if matched_po and match_confidence > 0.4:
        # Mode: MATCH
        # Build comparison data (reusing existing matching logic)
        po_items_by_id = {item.id: item for item in matched_po.items}
        po_items_remaining = set(po_items_by_id.keys())
        matches = []
        unmatched_invoice_items = []
        total_discrepancy = 0.0
        
        for item in items:
            best_match = None
            best_score = 0.0
            
            for po_item_id in po_items_remaining:
                po_item = po_items_by_id[po_item_id]
                if not po_item.product:
                    continue
                
                # SKU exact match
                if item.sku and po_item.product.sku:
                    if item.sku.upper() == po_item.product.sku.upper():
                        best_match = po_item
                        best_score = 1.0
                        break
                
                # Description similarity
                desc_score = similarity(item.description, po_item.product.name or "")
                if desc_score > best_score and desc_score > 0.5:
                    best_match = po_item
                    best_score = desc_score
            
            if best_match:
                po_items_remaining.discard(best_match.id)
                
                qty_diff = abs(item.quantity - best_match.quantity_ordered)
                price_diff = abs(item.unit_cost - best_match.unit_cost)
                
                discrepancy_parts = []
                if qty_diff > 0.01:
                    discrepancy_parts.append(f"Qty: PO={best_match.quantity_ordered}, Doc={item.quantity}")
                    total_discrepancy += qty_diff * best_match.unit_cost
                if price_diff > 0.01:
                    discrepancy_parts.append(f"Price: PO=${best_match.unit_cost:.2f}, Doc=${item.unit_cost:.2f}")
                    total_discrepancy += price_diff * item.quantity
                
                if qty_diff > 0.01 and price_diff > 0.01:
                    status = "quantity_price_diff"
                elif qty_diff > 0.01:
                    status = "quantity_diff"
                elif price_diff > 0.01:
                    status = "price_diff"
                else:
                    status = "matched"
                
                matches.append({
                    "po_item_id": best_match.id,
                    "po_description": best_match.product.name if best_match.product else None,
                    "po_quantity": best_match.quantity_ordered,
                    "po_quantity_received": best_match.quantity_received or 0,
                    "po_remaining_quantity": max(
                        0,
                        best_match.quantity_ordered - (best_match.quantity_received or 0),
                    ),
                    "po_unit_cost": best_match.unit_cost,
                    "invoice_sku": item.sku,
                    "invoice_description": item.description,
                    "invoice_quantity": item.quantity,
                    "invoice_unit_cost": item.unit_cost,
                    "invoice_line_total": item.line_total,
                    "match_status": status,
                    "confidence": best_score,
                    "discrepancy_details": "; ".join(discrepancy_parts) if discrepancy_parts else None
                })
            else:
                unmatched_invoice_items.append({
                    "sku": item.sku,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                    "line_total": item.line_total
                })
        
        unmatched_po_items = []
        for po_item_id in po_items_remaining:
            po_item = po_items_by_id[po_item_id]
            unmatched_po_items.append({
                "item_id": po_item.id,
                "product_name": po_item.product.name if po_item.product else f"Product #{po_item.product_id}",
                "quantity": po_item.quantity_ordered,
                "quantity_received": po_item.quantity_received or 0,
                "remaining_quantity": max(
                    0,
                    po_item.quantity_ordered - (po_item.quantity_received or 0),
                ),
                "unit_cost": po_item.unit_cost
            })
        
        return DocumentParseResult(
            mode="match",
            vendor_name=doc_vendor,
            po_number=doc_po_number,
            invoice_number=extraction_result.get("invoice_number"),
            document_date=extraction_result.get("invoice_date") or extraction_result.get("po_date"),
            currency=extraction_result.get("currency", "USD"),
            items=items,
            subtotal=extraction_result.get("subtotal", 0),
            shipping_cost=extraction_result.get("shipping_cost", 0),
            tax_amount=extraction_result.get("tax_amount", 0),
            total_amount=extraction_result.get("total_amount", 0),
            confidence=extraction_confidence,
            matched_po_id=matched_po.id,
            matched_po_number=f"PO-{matched_po.id}",
            matched_supplier_name=matched_po.supplier.name if matched_po.supplier else None,
            match_confidence=match_confidence,
            matches=matches,
            unmatched_po_items=unmatched_po_items,
            unmatched_invoice_items=unmatched_invoice_items,
            total_discrepancy=total_discrepancy
        )
    else:
        # Mode: CREATE
        # Try to fuzzy-match extracted items to existing products
        from src.crud.crud_product import product as crud_product
        from src.crud.crud_supplier_product import supplier_product as crud_sp
        from src.crud.crud_supplier_product_alias import supplier_product_alias as crud_alias
        from src.crud.crud_supplier import supplier as crud_supplier

        all_products = crud_product.get_multi(db=db, limit=500)
        
        # Determine if we matched a supplier from doc_vendor
        matched_supplier_id = None
        if doc_vendor:
            all_suppliers = crud_supplier.get_multi(db=db, limit=500)
            vendor_lower = doc_vendor.lower()
            for s in all_suppliers:
                if vendor_lower in s.name.lower() or s.name.lower() in vendor_lower:
                    matched_supplier_id = s.id
                    break

        # Load supplier specific products if we have a matched supplier
        supplier_products = []
        supplier_aliases = []
        if matched_supplier_id:
            supplier_products = crud_sp.get_by_supplier(db=db, supplier_id=matched_supplier_id)
            supplier_aliases = crud_alias.get_active_by_supplier(db=db, supplier_id=matched_supplier_id)
        
        for item in items:
            best_product_id = None
            best_variant_id = None
            best_score = 0.0
            
            # First, try to match against learned aliases approved by users.
            if supplier_aliases:
                item_sku = (item.sku or "").strip().lower()
                item_desc = item.description or ""
                for alias in supplier_aliases:
                    score = 0.0
                    if item_sku and alias.normalized_sku and item_sku == alias.normalized_sku:
                        score = 1.0
                    elif item_desc and alias.normalized_name:
                        score = similarity(item_desc, alias.alias_name or alias.normalized_name)

                    if score > best_score:
                        best_score = score
                        best_product_id = alias.product_id
                        best_variant_id = alias.variant_id

            # Then try the canonical supplier_product_name.
            if supplier_products and item.description and best_score < 0.9:
                for sp in supplier_products:
                    if sp.supplier_product_name:
                        score = similarity(item.description, sp.supplier_product_name)
                        if score > best_score:
                            best_score = score
                            best_product_id = sp.product_id
                            best_variant_id = None

            # If still not confident, check all products (fallback)
            if best_score < 0.6:
                for product in all_products:
                    # Try description vs product name
                    score = similarity(item.description, product.name or "")
                    if score > best_score:
                        best_score = score
                        best_product_id = product.id
                        best_variant_id = None
                    
                    # Also try SKU match (exact)
                    if item.sku and product.sku:
                        if item.sku.upper() == product.sku.upper():
                            best_product_id = product.id
                            best_variant_id = None
                            best_score = 1.0
                            break
            
            if best_score > 0.4 and best_product_id:
                item.matched_product_id = best_product_id
                item.matched_variant_id = best_variant_id
        
        return DocumentParseResult(
            mode="create",
            vendor_name=doc_vendor,
            po_number=doc_po_number,
            invoice_number=extraction_result.get("invoice_number"),
            document_date=extraction_result.get("invoice_date") or extraction_result.get("po_date"),
            currency=extraction_result.get("currency", "USD"),
            items=items,
            subtotal=extraction_result.get("subtotal", 0),
            shipping_cost=extraction_result.get("shipping_cost", 0),
            tax_amount=extraction_result.get("tax_amount", 0),
            total_amount=extraction_result.get("total_amount", 0),
            confidence=extraction_confidence
        )


# --- PO Ingestion Schemas (DEPRECATED - use /parse-document instead) ---
class ExtractedLineItemResponse(BaseModel):
    """Response schema for an extracted line item."""
    sku: str | None = None
    description: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    line_total: float = 0.0
    matched_product_id: int | None = None
    matched_variant_id: int | None = None


class POIngestionResponse(BaseModel):
    """Response schema for PO ingestion results."""
    supplier_name: str | None = None
    po_number: str | None = None
    po_date: str | None = None
    currency: str = "USD"
    payment_terms: str | None = None
    items: List[ExtractedLineItemResponse] = []
    subtotal: float = 0.0
    shipping_cost: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    extraction_method: str = "traditional"
    confidence_score: float = 0.0
    warnings: List[str] = []


@router.post("/ingest", response_model=POIngestionResponse)
async def ingest_purchase_order(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    use_ai: bool = Query(False, description="Enable AI enhancement for complex documents"),
):
    """
    Ingest a Purchase Order document (PDF, HTML, or TXT).
    
    Returns extracted data for preview before creating a PO.
    The user should review and confirm before calling POST / to create the actual record.
    
    Args:
        file: The PO document to ingest.
        use_ai: Whether to use AI enhancement (requires AI features enabled in settings).
    """
    from src.services.purchase_order_ingestion_service import POIngestionService
    
    # Validate file type
    allowed_types = {'.pdf', '.html', '.htm', '.txt', '.text'}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
    
    # Initialize service
    service = POIngestionService(ai_enabled=use_ai)
    
    # Ingest and parse
    try:
        result = service.ingest_file(file.filename or "document.txt", content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    
    # Convert to response schema
    items_response = [
        ExtractedLineItemResponse(
            sku=item.sku,
            description=item.description,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            line_total=item.line_total,
            matched_product_id=item.product_id
        )
        for item in result.items
    ]
    
    return POIngestionResponse(
        supplier_name=result.supplier_name,
        po_number=result.po_number,
        po_date=result.po_date.isoformat() if result.po_date else None,
        currency=result.currency,
        payment_terms=result.payment_terms,
        items=items_response,
        subtotal=result.subtotal,
        shipping_cost=result.shipping_cost,
        tax_amount=result.tax_amount,
        total_amount=result.total_amount,
        extraction_method=result.extraction_method,
        confidence_score=result.confidence_score,
        warnings=result.warnings
    )


# --- Invoice Parse & Match Schemas ---
class InvoiceMatchItem(BaseModel):
    """Result of matching an invoice item to a PO item."""
    po_item_id: int | None = None
    po_description: str | None = None
    po_quantity: float | None = None
    po_quantity_received: float | None = None
    po_remaining_quantity: float | None = None
    po_unit_cost: float | None = None
    
    invoice_sku: str | None = None
    invoice_description: str
    invoice_quantity: float
    invoice_unit_cost: float
    invoice_line_total: float
    
    match_status: str  # "matched", "quantity_diff", "price_diff", "unmatched"
    confidence: float
    discrepancy_details: str | None = None


class InvoiceMatchResult(BaseModel):
    """Result of parsing and matching an invoice against a PO."""
    invoice_number: str | None = None
    invoice_date: str | None = None
    vendor_name: str | None = None
    
    matches: List[InvoiceMatchItem] = []
    unmatched_po_items: List[dict] = []
    unmatched_invoice_items: List[dict] = []
    
    total_discrepancy: float = 0.0
    overall_confidence: float = 0.0
    extraction_confidence: float = 0.0


@router.post("/{id}/invoices/parse-and-match", response_model=InvoiceMatchResult)
async def parse_and_match_invoice(
    *,
    db: Session = Depends(get_db),
    id: int,
    file: UploadFile = File(...),
):
    """
    Parse an invoice document and match items against the PO.
    
    Uses AI to extract invoice data, then matches each invoice line item
    to the corresponding PO item by SKU or description similarity.
    
    Returns:
        - Matched items with discrepancy details
        - Unmatched PO items (missing from invoice)
        - Unmatched invoice items (extra items not in PO)
        - Overall confidence and discrepancy totals
    """
    from difflib import SequenceMatcher
    from src.services.adk.manager import ADKManager
    from src.services.adk.orchestrator import AgentOrchestrator
    from src.crud.crud_store_settings import store_settings as crud_store_settings
    
    # Verify PO exists
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Validate file type
    allowed_types = {'.pdf', '.png', '.jpg', '.jpeg', '.html', '.htm'}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
    
    # Determine MIME type
    mime_map = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.html': 'text/html',
        '.htm': 'text/html'
    }
    mime_type = mime_map.get(file_ext, 'application/octet-stream')
    
    # Get store settings for AI config
    settings = crud_store_settings.get_settings(db)
    if not settings or not settings.ai_enabled:
        raise HTTPException(
            status_code=400, 
            detail="AI features are disabled in Settings. Enable AI to use invoice parsing."
        )
    
    # Initialize ADK manager and orchestrator
    adk_manager = ADKManager(db)
    orchestrator = AgentOrchestrator(adk_manager)
    
    # Parse invoice using AI
    extraction_result = await orchestrator.parse_invoice(content, mime_type)
    
    if "error" in extraction_result:
        raise HTTPException(status_code=500, detail=extraction_result["error"])
    
    # Extract invoice data
    invoice_items = extraction_result.get("items", [])
    extraction_confidence = extraction_result.get("confidence", 0.5)
    
    # Build PO item lookup
    po_items_by_id = {item.id: item for item in po.items}
    po_items_remaining = set(po_items_by_id.keys())
    
    # Matching logic
    matches = []
    unmatched_invoice_items = []
    total_discrepancy = 0.0
    
    def similarity(a: str, b: str) -> float:
        """Calculate string similarity."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    for inv_item in invoice_items:
        inv_sku = inv_item.get("sku", "")
        inv_desc = inv_item.get("description", "")
        inv_qty = inv_item.get("quantity", 0)
        inv_cost = inv_item.get("unit_cost", 0)
        inv_total = inv_item.get("line_total", 0)
        
        best_match = None
        best_score = 0.0
        
        # Try to match by SKU first, then by description
        for po_item_id in po_items_remaining:
            po_item = po_items_by_id[po_item_id]
            po_product = po_item.product
            
            if not po_product:
                continue
            
            # SKU exact match (highest priority)
            if inv_sku and po_product.sku and inv_sku.upper() == po_product.sku.upper():
                best_match = po_item
                best_score = 1.0
                break
            
            # Description similarity
            po_desc = po_product.name or ""
            desc_score = similarity(inv_desc, po_desc)
            if desc_score > best_score and desc_score > 0.5:
                best_match = po_item
                best_score = desc_score
        
        if best_match:
            po_items_remaining.discard(best_match.id)
            
            # Determine match status and discrepancies
            qty_diff = abs(inv_qty - best_match.quantity_ordered)
            price_diff = abs(inv_cost - best_match.unit_cost)
            
            discrepancy_parts = []
            if qty_diff > 0.01:
                discrepancy_parts.append(f"Qty: PO={best_match.quantity_ordered}, Invoice={inv_qty}")
                total_discrepancy += qty_diff * best_match.unit_cost
            if price_diff > 0.01:
                discrepancy_parts.append(f"Price: PO=${best_match.unit_cost:.2f}, Invoice=${inv_cost:.2f}")
                total_discrepancy += price_diff * inv_qty
            
            if qty_diff > 0.01 and price_diff > 0.01:
                status = "quantity_price_diff"
            elif qty_diff > 0.01:
                status = "quantity_diff"
            elif price_diff > 0.01:
                status = "price_diff"
            else:
                status = "matched"
            
            matches.append(InvoiceMatchItem(
                po_item_id=best_match.id,
                po_description=best_match.product.name if best_match.product else None,
                po_quantity=best_match.quantity_ordered,
                po_quantity_received=best_match.quantity_received or 0,
                po_remaining_quantity=max(
                    0,
                    best_match.quantity_ordered - (best_match.quantity_received or 0),
                ),
                po_unit_cost=best_match.unit_cost,
                invoice_sku=inv_sku,
                invoice_description=inv_desc,
                invoice_quantity=inv_qty,
                invoice_unit_cost=inv_cost,
                invoice_line_total=inv_total,
                match_status=status,
                confidence=best_score,
                discrepancy_details="; ".join(discrepancy_parts) if discrepancy_parts else None
            ))
        else:
            unmatched_invoice_items.append({
                "sku": inv_sku,
                "description": inv_desc,
                "quantity": inv_qty,
                "unit_cost": inv_cost,
                "line_total": inv_total
            })
    
    # Build unmatched PO items list
    unmatched_po_items = []
    for po_item_id in po_items_remaining:
        po_item = po_items_by_id[po_item_id]
        unmatched_po_items.append({
            "item_id": po_item.id,
            "product_name": po_item.product.name if po_item.product else f"Product #{po_item.product_id}",
            "quantity": po_item.quantity_ordered,
            "quantity_received": po_item.quantity_received or 0,
            "remaining_quantity": max(
                0,
                po_item.quantity_ordered - (po_item.quantity_received or 0),
            ),
            "unit_cost": po_item.unit_cost
        })
    
    # Calculate overall confidence
    if matches:
        overall_confidence = sum(m.confidence for m in matches) / len(matches) * extraction_confidence
    else:
        overall_confidence = extraction_confidence * 0.5
    
    return InvoiceMatchResult(
        invoice_number=extraction_result.get("invoice_number"),
        invoice_date=extraction_result.get("invoice_date"),
        vendor_name=extraction_result.get("vendor_name"),
        matches=matches,
        unmatched_po_items=unmatched_po_items,
        unmatched_invoice_items=unmatched_invoice_items,
        total_discrepancy=total_discrepancy,
        overall_confidence=overall_confidence,
        extraction_confidence=extraction_confidence
    )
