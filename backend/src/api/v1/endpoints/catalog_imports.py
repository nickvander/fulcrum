"""
Catalog import review endpoints.

Mirrors the supplier-document import-review flow from
`backend/src/api/v1/endpoints/purchase_orders.py` but produces new `Product`
rows on approval instead of a `PurchaseOrder`. CSV uploads parse synchronously
via `CatalogIngestionService`; PDF / image uploads go through the AI agent
orchestrator and only succeed when the user has both enabled AI in settings
and configured an API key for the active provider.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user, get_db
from src.core.errors import LocalizedHTTPException
from src.crud import crud_product
from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.crud.crud_supplier import supplier as crud_supplier
from src.crud.crud_supplier_product import supplier_product as crud_supplier_product
from src.models.catalog_import import CatalogImport
from src.models.user import User
from src.schemas.product import ProductCreate
from src.schemas.supplier_product import SupplierProductCreate
from src.services.adk.manager import ADKManager
from src.services.adk.orchestrator import AgentOrchestrator
from src.services.catalog_ingestion_service import (
    AI_SUFFIXES,
    CSV_SUFFIXES,
    catalog_ingestion_service,
    extracted_item_to_dict,
    file_suffix,
    is_ai_required,
)


router = APIRouter()


# MIME types that match `AI_SUFFIXES` — used to set the right Part type when
# handing the file to Gemini multimodal.
_AI_MIME_BY_SUFFIX = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "avif": "image/avif",
}


class CatalogImportItem(BaseModel):
    sku: str | None = None
    name: str = ""
    description: str | None = None
    cost_price: float | None = None
    default_resale_price: float | None = None
    category: str | None = None
    brand: str | None = None
    supplier_sku: str | None = None
    raw: dict = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    selected: bool = True


class CatalogImportRead(BaseModel):
    id: int
    file_name: str
    content_type: str | None = None
    source: str
    status: str
    supplier_id: int | None = None
    extracted_data: dict
    warnings: List[str] = []
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class CatalogImportApproveRequest(BaseModel):
    supplier_id: int | None = None
    items: List[CatalogImportItem]


class CatalogImportApproveResponse(BaseModel):
    import_review: CatalogImportRead
    created_product_ids: List[int]
    skipped_count: int = 0
    skipped_reasons: List[str] = Field(default_factory=list)


def _read_response(review: CatalogImport) -> CatalogImportRead:
    return CatalogImportRead(
        id=review.id,
        file_name=review.file_name,
        content_type=review.content_type,
        source=review.source or "csv",
        status=review.status,
        supplier_id=review.supplier_id,
        extracted_data=review.extracted_data or {},
        warnings=review.warnings or [],
        created_at=review.created_at,
        reviewed_at=review.reviewed_at,
    )


def _pending(db: Session, review_id: int) -> CatalogImport:
    review = db.query(CatalogImport).filter(CatalogImport.id == review_id).first()
    if not review:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.catalogImport.reviewNotFound",
            detail="Catalog import review not found",
        )
    if review.status != "pending":
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.catalogImport.reviewNotPending",
            detail="Only pending catalog import reviews can be modified",
        )
    return review


class CatalogImportCapabilities(BaseModel):
    """Shape what the dialog can offer the user. Frontend uses this to set the
    file input's `accept` list and to decide whether to show an AI hint."""
    csv: bool = True
    ai: bool = False  # ai_enabled AND active provider has an API key
    ai_enabled: bool = False
    ai_configured: bool = False
    ai_provider: str | None = None
    accepted_extensions: list[str] = Field(default_factory=lambda: sorted(CSV_SUFFIXES))


@router.get("/capabilities", response_model=CatalogImportCapabilities)
def get_catalog_import_capabilities(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tell the frontend what file types this workspace can import.

    Always offers CSV/TSV. PDF and images are offered only when AI is both
    enabled in Settings and the active provider has a configured API key.
    """
    settings = crud_store_settings.get_settings(db)
    ai_enabled = bool(settings and settings.ai_enabled)
    provider = (settings.ai_provider if settings else None) or "google"
    manager = ADKManager(db)
    ai_configured = manager.is_configured(provider)
    ai_ready = ai_enabled and ai_configured

    accepted = sorted(CSV_SUFFIXES)
    if ai_ready:
        accepted = sorted(CSV_SUFFIXES | AI_SUFFIXES)

    return CatalogImportCapabilities(
        csv=True,
        ai=ai_ready,
        ai_enabled=ai_enabled,
        ai_configured=ai_configured,
        ai_provider=provider,
        accepted_extensions=accepted,
    )


@router.post("/reviews", response_model=CatalogImportRead)
async def create_catalog_import_review(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    supplier_id: int | None = Query(None, description="Optional supplier to link new products to"),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a catalog file, parse it (CSV synchronously / PDF + image via AI),
    and stage a review row.
    """
    content = await file.read()
    if not content:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.catalogImport.emptyFile",
            detail="Uploaded catalog file is empty",
        )

    if supplier_id is not None and not crud_supplier.get(db=db, id=supplier_id):
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.purchaseOrder.supplierNotFound",
            detail="Supplier not found",
        )

    filename = file.filename or "catalog.csv"
    suffix = file_suffix(filename)
    source = "csv"
    warnings: list[str] = []

    if is_ai_required(filename):
        # PDF / image upload — must be backed by a working AI provider
        manager = ADKManager(db)
        if not manager.is_ready():
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.catalogImport.aiRequiredForFileType",
                params={"extension": f".{suffix}"},
                detail=(
                    f"Importing .{suffix} catalogs requires AI to be enabled and "
                    "an API key configured for the active provider in Settings."
                ),
            )

        mime_type = _AI_MIME_BY_SUFFIX.get(suffix, file.content_type or "application/octet-stream")
        orchestrator = AgentOrchestrator(manager)
        ai_result = await orchestrator.parse_catalog(content, mime_type)
        if "error" in ai_result:
            raise LocalizedHTTPException(
                status_code=502,
                code="apiErrors.catalogImport.aiExtractionFailed",
                params={"reason": ai_result["error"]},
                detail=f"AI catalog extraction failed: {ai_result['error']}",
            )

        parsed = catalog_ingestion_service.ingest_ai_result(ai_result)
        source = "ai"
    else:
        parsed = catalog_ingestion_service.ingest(file_name=filename, content=content)

    extracted = {"items": [extracted_item_to_dict(i) for i in parsed.items]}
    warnings.extend(parsed.warnings)
    if not parsed.items:
        warnings.append("No importable rows found.")

    review = CatalogImport(
        file_name=filename,
        content_type=file.content_type,
        source=source,
        status="pending",
        supplier_id=supplier_id,
        extracted_data=extracted,
        warnings=warnings,
        created_by_id=current_user.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _read_response(review)


@router.get("/reviews", response_model=List[CatalogImportRead])
def list_catalog_import_reviews(
    *,
    db: Session = Depends(get_db),
    status: str | None = Query("pending"),
    supplier_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(CatalogImport).order_by(
        CatalogImport.created_at.desc(),
        CatalogImport.id.desc(),
    )
    if status and status.lower() != "all":
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            query = query.filter(CatalogImport.status == statuses[0])
        elif statuses:
            query = query.filter(CatalogImport.status.in_(statuses))
    if supplier_id is not None:
        query = query.filter(CatalogImport.supplier_id == supplier_id)
    return [_read_response(r) for r in query.limit(limit).all()]


@router.get("/reviews/{review_id}", response_model=CatalogImportRead)
def get_catalog_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    current_user: User = Depends(get_current_active_user),
):
    review = db.query(CatalogImport).filter(CatalogImport.id == review_id).first()
    if not review:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.catalogImport.reviewNotFound",
            detail="Catalog import review not found",
        )
    return _read_response(review)


@router.post("/reviews/{review_id}/approve", response_model=CatalogImportApproveResponse)
def approve_catalog_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    request: CatalogImportApproveRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Create `Product` rows from selected items, optionally linking each to a
    `SupplierProduct` when a supplier is supplied."""
    review = _pending(db, review_id)

    supplier_id = request.supplier_id if request.supplier_id is not None else review.supplier_id
    if supplier_id is not None and not crud_supplier.get(db=db, id=supplier_id):
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.purchaseOrder.supplierNotFound",
            detail="Supplier not found",
        )

    selected = [i for i in request.items if i.selected and (i.name or "").strip()]
    if not selected:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.catalogImport.nothingSelected",
            detail="Select at least one row with a product name before approving",
        )

    created_ids: list[int] = []
    skipped_reasons: list[str] = []

    for item in selected:
        sku = (item.sku or "").strip() or None
        if sku and crud_product.product.get_by_sku(db, sku=sku):
            skipped_reasons.append(f"SKU '{sku}' already exists; skipped.")
            continue

        product_in = ProductCreate(
            name=item.name.strip(),
            sku=sku,
            description=item.description,
            cost_price=item.cost_price,
            default_resale_price=item.default_resale_price,
            category=item.category,
            brand=item.brand,
        )
        product = crud_product.product.create(db, obj_in=product_in)
        created_ids.append(product.id)

        if supplier_id is not None:
            try:
                crud_supplier_product.create(
                    db,
                    obj_in=SupplierProductCreate(
                        product_id=product.id,
                        supplier_id=supplier_id,
                        supplier_sku=item.supplier_sku or sku,
                        cost_price=item.cost_price or 0.0,
                    ),
                )
            except Exception as exc:  # pragma: no cover — never abort approval over link failure
                skipped_reasons.append(
                    f"Could not link supplier for '{item.name}': {exc.__class__.__name__}"
                )

    review.status = "approved"
    review.reviewed_at = datetime.utcnow()
    review.reviewed_by_id = current_user.id
    if supplier_id is not None and review.supplier_id is None:
        review.supplier_id = supplier_id
    db.add(review)
    db.commit()
    db.refresh(review)

    return CatalogImportApproveResponse(
        import_review=_read_response(review),
        created_product_ids=created_ids,
        skipped_count=len(skipped_reasons),
        skipped_reasons=skipped_reasons,
    )


@router.post("/reviews/{review_id}/reject", response_model=CatalogImportRead)
def reject_catalog_import_review(
    *,
    db: Session = Depends(get_db),
    review_id: int,
    current_user: User = Depends(get_current_active_user),
):
    review = _pending(db, review_id)
    review.status = "rejected"
    review.reviewed_at = datetime.utcnow()
    review.reviewed_by_id = current_user.id
    db.add(review)
    db.commit()
    db.refresh(review)
    return _read_response(review)
