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
from src.models.import_template import ImportTemplate
from src.models.supplier import Supplier
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


def _fuzzy_match_supplier(db: Session, vendor_name: str | None) -> Supplier | None:
    """Best-effort match of a vendor name extracted from a document to an
    existing Supplier row. Strategy mirrors `_find_supplier_id_for_vendor`
    in purchase_orders.py — case-insensitive substring match in either
    direction, first hit wins.

    Returns the Supplier row (not just the id) so the endpoint can echo the
    matched name back to the UI for transparency.
    """
    if not vendor_name:
        return None

    vendor_lower = vendor_name.strip().lower()
    if not vendor_lower:
        return None

    # First pass: exact case-insensitive match (avoid mis-matching when one
    # supplier name is a substring of another, e.g. "Acme" vs "Acme Tools")
    for supplier in db.query(Supplier).limit(500).all():
        if supplier.name.lower() == vendor_lower:
            return supplier

    # Second pass: substring match in either direction
    for supplier in db.query(Supplier).limit(500).all():
        sup_lower = supplier.name.lower()
        if vendor_lower in sup_lower or sup_lower in vendor_lower:
            return supplier

    return None


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
    # AI-extracted vendor name (only set when source == "ai")
    detected_vendor_name: str | None = None
    # If we auto-linked the detected vendor to an existing supplier, this is
    # that supplier's display name so the UI can show "Linked: VendorName"
    # without an extra round-trip.
    auto_linked_supplier_name: str | None = None

    model_config = {"from_attributes": True}


class CatalogImportApproveRequest(BaseModel):
    supplier_id: int | None = None
    items: List[CatalogImportItem]


class CatalogImportApproveResponse(BaseModel):
    import_review: CatalogImportRead
    created_product_ids: List[int]
    skipped_count: int = 0
    skipped_reasons: List[str] = Field(default_factory=list)


# --- Named import templates -------------------------------------------------
#
# The "Map & Template" UX from usability-roadmap.md #4: a user uploads a
# supplier's catalog whose headers don't match any of the alias entries,
# manually maps columns once, saves the map as a named template, and on
# every future upload picks the template to skip the alias auto-detection.


# Set of canonical fields a template's `column_map` is allowed to reference.
# Kept here next to the CatalogImport schema so an out-of-date map (e.g. a
# template that mentions a field we since removed) is caught at upload time
# instead of producing silently-wrong rows.
_ALLOWED_CANONICAL_FIELDS = {
    "sku", "name", "description", "cost_price", "default_resale_price",
    "category", "brand", "supplier_sku",
}


def _validate_column_map(column_map: dict[str, str]) -> None:
    """Reject a template whose values mention fields the parser doesn't
    know about. This is the only sanity check we run — empty source
    headers are silently dropped by the parser when the file lands."""
    for source_header, canonical in column_map.items():
        if canonical not in _ALLOWED_CANONICAL_FIELDS:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.catalogImport.invalidColumnMap",
                params={"field": canonical},
                detail=f"Unknown Fulcrum field '{canonical}' in column map",
            )


class ImportTemplatePreview(BaseModel):
    """First few rows + headers, returned without saving anything. The
    "Map & Template" dialog uses this to populate the mapping screen
    before the user picks a column for each source header."""
    headers: List[str]
    sample_rows: List[dict]
    detected_field_map: dict[str, str]
    """Best-effort {canonical_field: actual_header} from the existing alias
    auto-detection — the UI can pre-fill the dropdowns with this so the
    user only re-maps what was missed."""


class ImportTemplateBase(BaseModel):
    name: str
    column_map: dict[str, str]
    notes: str | None = None


class ImportTemplateCreate(ImportTemplateBase):
    pass


class ImportTemplateUpdate(BaseModel):
    name: str | None = None
    column_map: dict[str, str] | None = None
    notes: str | None = None


class ImportTemplateRead(ImportTemplateBase):
    id: int
    source_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _template_response(t: ImportTemplate) -> ImportTemplateRead:
    return ImportTemplateRead(
        id=t.id,
        name=t.name,
        source_type=t.source_type,
        column_map=t.column_map or {},
        notes=t.notes,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _get_template_or_404(db: Session, template_id: int) -> ImportTemplate:
    template = (
        db.query(ImportTemplate)
        .filter(ImportTemplate.id == template_id, ImportTemplate.source_type == "catalog")
        .first()
    )
    if not template:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.catalogImport.templateNotFound",
            detail="Import template not found",
        )
    return template


def _read_response(review: CatalogImport) -> CatalogImportRead:
    extracted = review.extracted_data or {}
    return CatalogImportRead(
        id=review.id,
        file_name=review.file_name,
        content_type=review.content_type,
        source=review.source or "csv",
        status=review.status,
        supplier_id=review.supplier_id,
        extracted_data=extracted,
        warnings=review.warnings or [],
        created_at=review.created_at,
        reviewed_at=review.reviewed_at,
        detected_vendor_name=extracted.get("vendor_name"),
        auto_linked_supplier_name=extracted.get("auto_linked_supplier_name"),
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
    template_id: int | None = Query(
        None,
        description="Optional saved ImportTemplate id; overrides alias auto-detection for CSV uploads",
    ),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a catalog file, parse it (CSV synchronously / PDF + image via AI),
    and stage a review row.

    When `template_id` is set and the file is a CSV/TSV, the template's
    `column_map` replaces the alias auto-detection for that upload — this
    is the "Map & Template" path for suppliers whose headers don't match
    any built-in alias.
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
        column_map: dict[str, str] | None = None
        if template_id is not None:
            template = _get_template_or_404(db, template_id)
            column_map = template.column_map or {}
        parsed = catalog_ingestion_service.ingest(
            file_name=filename, content=content, column_map=column_map,
        )

    extracted = {"items": [extracted_item_to_dict(i) for i in parsed.items]}
    if parsed.vendor_name:
        extracted["vendor_name"] = parsed.vendor_name
    warnings.extend(parsed.warnings)
    if not parsed.items:
        warnings.append("No importable rows found.")

    # If AI extracted a vendor name and the user didn't pick a supplier at
    # upload time, try to auto-link to an existing supplier. The user can
    # still change it on the review step.
    if source == "ai" and supplier_id is None and parsed.vendor_name:
        matched = _fuzzy_match_supplier(db, parsed.vendor_name)
        if matched:
            supplier_id = matched.id
            extracted["auto_linked_supplier_name"] = matched.name
            warnings.append(
                f"Auto-linked supplier '{matched.name}' from document vendor "
                f"'{parsed.vendor_name}'. Confirm before approving."
            )
        else:
            extracted["auto_linked_supplier_name"] = None
            warnings.append(
                f"Document vendor '{parsed.vendor_name}' did not match any "
                "existing supplier. Pick one manually before approving."
            )

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


# --- Template preview + CRUD ------------------------------------------------


@router.post("/templates/preview", response_model=ImportTemplatePreview)
async def preview_catalog_for_mapping(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    sample_size: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_active_user),
):
    """Inspect a CSV without staging a review. Returns the headers, the
    first N data rows, and what the alias auto-detector would have
    matched — the UI uses this to populate the column-mapping screen so
    the user only re-maps headers the auto-detector missed."""
    content = await file.read()
    if not content:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.catalogImport.emptyFile",
            detail="Uploaded file is empty",
        )

    import csv as csv_mod
    import io as io_mod
    from src.services.catalog_ingestion_service import (
        _build_field_map,
        _sniff_dialect,
    )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="ignore")

    dialect = _sniff_dialect(text[:4096])
    reader = csv_mod.DictReader(io_mod.StringIO(text), dialect=dialect)
    headers = list(reader.fieldnames or [])
    detected = _build_field_map(headers)
    sample_rows = [row for row, _ in zip(reader, range(sample_size))]
    return ImportTemplatePreview(
        headers=headers,
        sample_rows=sample_rows,
        detected_field_map=detected,
    )


@router.get("/templates", response_model=List[ImportTemplateRead])
def list_catalog_import_templates(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List saved catalog import templates. Returns every template across
    users for now — single-tenant workspace assumption — so a buyer can
    pick up a template a colleague saved."""
    templates = (
        db.query(ImportTemplate)
        .filter(ImportTemplate.source_type == "catalog")
        .order_by(ImportTemplate.name.asc())
        .all()
    )
    return [_template_response(t) for t in templates]


@router.post("/templates", response_model=ImportTemplateRead)
def create_catalog_import_template(
    *,
    db: Session = Depends(get_db),
    request: ImportTemplateCreate,
    current_user: User = Depends(get_current_active_user),
):
    name = (request.name or "").strip()
    if not name:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.catalogImport.templateNameRequired",
            detail="Template name is required",
        )
    _validate_column_map(request.column_map or {})

    # Reject duplicate (user, name) pairs explicitly so the UI shows a
    # clean error instead of a 500 on the unique constraint.
    existing = (
        db.query(ImportTemplate)
        .filter(
            ImportTemplate.created_by_id == current_user.id,
            ImportTemplate.source_type == "catalog",
            ImportTemplate.name == name,
        )
        .first()
    )
    if existing:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.catalogImport.templateNameExists",
            params={"name": name},
            detail="A template with this name already exists",
        )

    template = ImportTemplate(
        name=name,
        source_type="catalog",
        column_map=request.column_map or {},
        notes=request.notes,
        created_by_id=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_response(template)


@router.put("/templates/{template_id}", response_model=ImportTemplateRead)
def update_catalog_import_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    request: ImportTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
):
    template = _get_template_or_404(db, template_id)
    if request.name is not None:
        template.name = request.name.strip()
        if not template.name:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.catalogImport.templateNameRequired",
                detail="Template name is required",
            )
    if request.column_map is not None:
        _validate_column_map(request.column_map)
        template.column_map = request.column_map
    if request.notes is not None:
        template.notes = request.notes

    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_response(template)


@router.delete("/templates/{template_id}", response_model=ImportTemplateRead)
def delete_catalog_import_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
):
    template = _get_template_or_404(db, template_id)
    snapshot = _template_response(template)
    db.delete(template)
    db.commit()
    return snapshot
