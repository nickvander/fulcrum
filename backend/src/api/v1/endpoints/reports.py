"""
Operational reports surface. Exposes the low-stock report used by the
dashboard widget plus reusable export endpoints (CSV + PDF) that all share
the same `report_export` helpers — see `src/services/report_export.py`.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional


from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.api.dependencies import get_current_active_user
from src.core.errors import LocalizedHTTPException
from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.database import get_db
from src.models.inventory import InventoryAdjustment, InventoryItem
from src.models.order import SalesOrder, SalesOrderItem
from src.models.product import Product
from src.models.product_inventory_settings import ProductInventorySettings
from src.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from src.models.purchase_order_item import PurchaseOrderItem
from src.models.supplier_product import SupplierProduct
from src.models.user import User
from src.services.inventory_service import inventory_service
from src.services.report_export import (
    ReportColumn,
    ReportTable,
    fmt_currency,
    fmt_date,
    fmt_float,
    fmt_int,
    fmt_percent,
    stream_csv,
    stream_pdf,
)


router = APIRouter()


class LowStockRow(BaseModel):
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    supplier_id: Optional[int] = None
    on_hand: int
    threshold: int
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    suggested_reorder_qty: int
    daily_velocity: float
    days_of_inventory: float
    severity: str  # "critical" (out of stock), "low" (under threshold), "watch" (within 25% buffer)


class LowStockReport(BaseModel):
    rows: List[LowStockRow]
    total_critical: int
    total_low: int
    total_watch: int


@router.get("/low-stock", response_model=LowStockReport)
def low_stock_report(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    velocity_window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> LowStockReport:
    """
    Returns products at or below their effective low-stock threshold,
    along with sales velocity and a suggested reorder quantity.

    Threshold precedence (highest to lowest):
      1. Product.reorder_point (if set)
      2. ProductInventorySettings.low_stock_quantity_threshold (if set)
      3. StoreSettings.low_stock_quantity_default (always set)

    Suggested reorder qty:
      - Product.reorder_quantity if set, else
      - 30 * daily_velocity rounded up to a sane minimum of (threshold * 2),
        so even slow-moving items get a usable batch suggestion.

    Severity:
      - "critical" — on_hand == 0
      - "low"      — on_hand <= threshold
      - "watch"    — on_hand <= threshold * 1.25 (early warning band)
    """
    settings = crud_store_settings.get_settings(db)
    store_default = (
        settings.low_stock_quantity_default
        if settings and settings.low_stock_quantity_default is not None
        else 10
    )

    on_hand_rows = (
        db.query(
            InventoryItem.product_id,
            func.coalesce(func.sum(InventoryItem.quantity), 0).label("on_hand"),
        )
        .group_by(InventoryItem.product_id)
        .all()
    )
    on_hand_by_product = {pid: int(qty or 0) for pid, qty in on_hand_rows}

    pis_rows = db.query(ProductInventorySettings).all()
    pis_by_product = {row.product_id: row for row in pis_rows}

    products = db.query(Product).order_by(Product.id.asc()).limit(2000).all()

    candidates: List[LowStockRow] = []
    for product in products:
        on_hand = on_hand_by_product.get(product.id, 0)
        pis = pis_by_product.get(product.id)
        threshold = (
            product.reorder_point
            if product.reorder_point is not None
            else (
                pis.low_stock_quantity_threshold
                if pis and pis.low_stock_quantity_threshold is not None
                else store_default
            )
        )
        threshold = int(threshold)
        watch_band = int(threshold * 1.25) if threshold > 0 else 0

        if on_hand > watch_band:
            continue  # plenty of stock — skip

        velocity = inventory_service.calculate_sales_velocity(
            db, product.id, days=velocity_window_days
        )
        if velocity > 0:
            days_left = round(on_hand / velocity, 1)
        else:
            days_left = 999.0

        if product.reorder_quantity is not None:
            suggested = int(product.reorder_quantity)
        else:
            velocity_suggestion = int(round(velocity * 30))
            floor_suggestion = max(threshold * 2, 1)
            suggested = max(velocity_suggestion, floor_suggestion)

        if on_hand == 0:
            severity = "critical"
        elif on_hand <= threshold:
            severity = "low"
        else:
            severity = "watch"

        candidates.append(
            LowStockRow(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                supplier_id=product.supplier_id,
                on_hand=on_hand,
                threshold=threshold,
                reorder_point=product.reorder_point,
                reorder_quantity=product.reorder_quantity,
                suggested_reorder_qty=suggested,
                daily_velocity=round(velocity, 2),
                days_of_inventory=days_left,
                severity=severity,
            )
        )

    # Sort: most urgent first (critical → low → watch), then by days_of_inventory
    severity_order = {"critical": 0, "low": 1, "watch": 2}
    candidates.sort(key=lambda r: (severity_order[r.severity], r.days_of_inventory))

    return LowStockReport(
        rows=candidates[:limit],
        total_critical=sum(1 for r in candidates if r.severity == "critical"),
        total_low=sum(1 for r in candidates if r.severity == "low"),
        total_watch=sum(1 for r in candidates if r.severity == "watch"),
    )


# ---------------------------------------------------------------------------
# Exports — both CSV and PDF go through `report_export`
# ---------------------------------------------------------------------------

# Severity → row background color in the PDF. Defined once so both the
# severity check above and the PDF coloring stay in sync.
_SEVERITY_BG = {
    "critical": "#fde7e7",  # light red
    "low":      "#fff4d6",  # light amber
    "watch":    "#f0f4ff",  # light blue
}


def _low_stock_table(report: LowStockReport) -> ReportTable:
    """Build the `ReportTable` description for low-stock. Shared by CSV +
    PDF so column order, headers, and formatters stay aligned."""
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ReportTable(
        title="Fulcrum — Low-Stock Report",
        subtitle=(
            f"Generated {date_stamp} · {report.total_critical} critical · "
            f"{report.total_low} low · {report.total_watch} watch"
        ),
        filename_stem="fulcrum-low-stock",
        empty_message="No products are at or below threshold.",
        # CSV keeps the snake_case keys for back-compat with pre-refactor
        # consumers; the PDF uses the human headers via `header`.
        columns=[
            ReportColumn("product_id",            "Product ID"),
            ReportColumn("product_sku",           "SKU"),
            ReportColumn("product_name",          "Product"),
            ReportColumn("severity",              "Severity"),
            ReportColumn("on_hand",               "On hand",        align="right", formatter=fmt_int),
            ReportColumn("threshold",             "Threshold",      align="right", formatter=fmt_int),
            ReportColumn("reorder_point",         "Reorder pt",     align="right", formatter=fmt_int),
            ReportColumn("reorder_quantity",      "Reorder qty",    align="right", formatter=fmt_int),
            ReportColumn("suggested_reorder_qty", "Suggested",      align="right", formatter=fmt_int),
            ReportColumn("daily_velocity",        "Daily velocity", align="right", formatter=fmt_float(2)),
            ReportColumn("days_of_inventory",     "Days left",      align="right", formatter=fmt_float(1)),
        ],
        rows=report.rows,
        row_style=lambda row: {"background": _SEVERITY_BG[row.severity]} if row.severity in _SEVERITY_BG else None,
    )


@router.get("/low-stock/export")
def export_low_stock_csv(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(500, ge=1, le=5000),
    velocity_window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the low-stock report as a CSV download.

    Columns mirror the rows in the JSON report — same data, just in a shape
    Excel / Google Sheets opens directly. Default `limit` is 500 (vs. 50 on
    the JSON endpoint) because the export use case is "give me everything";
    the cap stays at 5000.
    """
    report = low_stock_report(
        db=db, limit=limit, velocity_window_days=velocity_window_days,
        current_user=current_user,
    )
    return stream_csv(_low_stock_table(report))


@router.get("/low-stock/export-pdf")
def export_low_stock_pdf(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(500, ge=1, le=5000),
    velocity_window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Render the low-stock report as a printable PDF.

    Same data + limits as the CSV export, plus severity-colored rows so the
    buyer can scan the page at a glance.
    """
    report = low_stock_report(
        db=db, limit=limit, velocity_window_days=velocity_window_days,
        current_user=current_user,
    )
    return stream_pdf(_low_stock_table(report))


# ---------------------------------------------------------------------------
# Inventory snapshot — per-product point-in-time inventory value report.
# Distinct from low-stock: this lists every active product with its on-hand
# quantity and computed cost / retail values, the kind of report an
# accountant asks for at quarter-end.
# ---------------------------------------------------------------------------


class InventorySnapshotRow(BaseModel):
    product_id: int
    product_sku: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    on_hand: int
    cost_price: float
    inventory_value_cost: float
    default_resale_price: float
    inventory_value_retail: float
    days_of_inventory: float


def _build_inventory_snapshot(db: Session, *, limit: int) -> list[InventorySnapshotRow]:
    """Pull every non-bundle Product with its summed inventory + computed
    cost/retail value. Bundles are excluded because their value is derived
    from component stock, not counted directly."""
    sub_qty = (
        db.query(
            InventoryItem.product_id.label("pid"),
            func.coalesce(func.sum(InventoryItem.quantity), 0).label("total"),
        )
        .group_by(InventoryItem.product_id)
        .subquery()
    )

    products = (
        db.query(Product, func.coalesce(sub_qty.c.total, 0))
        .outerjoin(sub_qty, sub_qty.c.pid == Product.id)
        .filter(Product.is_bundle.is_(False))
        .order_by(Product.name.asc())
        .limit(limit)
        .all()
    )

    rows: list[InventorySnapshotRow] = []
    for product, on_hand_raw in products:
        on_hand = int(on_hand_raw or 0)
        cost = float(product.cost_price or 0.0)
        resale = float(product.default_resale_price or 0.0)
        rows.append(
            InventorySnapshotRow(
                product_id=product.id,
                product_sku=product.sku,
                product_name=product.name,
                category=product.category,
                on_hand=on_hand,
                cost_price=cost,
                inventory_value_cost=on_hand * cost,
                default_resale_price=resale,
                inventory_value_retail=on_hand * resale,
                days_of_inventory=inventory_service.calculate_days_of_inventory(db, product.id),
            )
        )
    return rows


def _inventory_snapshot_table(rows: list[InventorySnapshotRow]) -> ReportTable:
    """One row per product with cost/retail inventory values. Same shared
    streamer as every other export."""
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_cost = sum(r.inventory_value_cost for r in rows)
    total_retail = sum(r.inventory_value_retail for r in rows)
    return ReportTable(
        title="Fulcrum — Inventory Snapshot",
        subtitle=(
            f"Generated {date_stamp} · {len(rows)} products · "
            f"cost value ${total_cost:,.2f} · retail value ${total_retail:,.2f}"
        ),
        filename_stem="fulcrum-inventory-snapshot",
        empty_message="No products with active inventory.",
        columns=[
            ReportColumn("product_id",             "Product ID"),
            ReportColumn("product_sku",            "SKU"),
            ReportColumn("product_name",           "Product"),
            ReportColumn("category",               "Category"),
            ReportColumn("on_hand",                "On hand",           align="right", formatter=fmt_int),
            ReportColumn("cost_price",             "Unit cost",         align="right", formatter=fmt_currency),
            ReportColumn("inventory_value_cost",   "Value at cost",     align="right", formatter=fmt_currency),
            ReportColumn("default_resale_price",   "Retail price",      align="right", formatter=fmt_currency),
            ReportColumn("inventory_value_retail", "Value at retail",   align="right", formatter=fmt_currency),
            ReportColumn("days_of_inventory",      "Days of inventory", align="right", formatter=fmt_float(1)),
        ],
        rows=rows,
    )


@router.get("/inventory-snapshot/export")
def export_inventory_snapshot_csv(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product inventory snapshot as a CSV. Includes on-hand qty + value
    at cost + value at retail. Useful for quarter-end inventory accounting.

    Bundles are excluded because their value is implicit in their
    components. Default limit is 2000 (cap 10000) — exports are "give me
    everything" use cases."""
    rows = _build_inventory_snapshot(db, limit=limit)
    return stream_csv(_inventory_snapshot_table(rows))


@router.get("/inventory-snapshot/export-pdf")
def export_inventory_snapshot_pdf(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product inventory snapshot as a printable PDF."""
    rows = _build_inventory_snapshot(db, limit=limit)
    return stream_pdf(_inventory_snapshot_table(rows))


# ---------------------------------------------------------------------------
# Inventory adjustment audit log — every quantity change with who/why/when.
# Used for stockout investigations + compliance audits.
# ---------------------------------------------------------------------------


def _build_inventory_adjustment_rows(
    db: Session,
    *,
    product_id: Optional[int],
    after: Optional[datetime],
    before: Optional[datetime],
    limit: int,
) -> list[dict]:
    from sqlalchemy.orm import joinedload as _joinedload  # local to avoid widening top imports

    query = (
        db.query(InventoryAdjustment)
        .options(_joinedload(InventoryAdjustment.product))
        .order_by(InventoryAdjustment.timestamp.desc().nullslast(), InventoryAdjustment.id.desc())
    )
    if product_id is not None:
        query = query.filter(InventoryAdjustment.product_id == product_id)
    if after is not None:
        query = query.filter(InventoryAdjustment.timestamp >= after)
    if before is not None:
        query = query.filter(InventoryAdjustment.timestamp <= before)

    rows: list[dict] = []
    for adj in query.limit(limit).all():
        product = adj.product
        rows.append({
            "timestamp":    adj.timestamp or adj.created_at,
            "product_id":   adj.product_id,
            "product_sku":  product.sku if product else "",
            "product_name": product.name if product else "",
            "adjustment":   adj.adjustment,
            "reason":       adj.reason or "",
            "created_by":   adj.created_by or "",
        })
    return rows


def _inventory_adjustment_table(rows: list[dict]) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    net = sum(r["adjustment"] for r in rows)
    return ReportTable(
        title="Fulcrum — Inventory Adjustment Audit Log",
        subtitle=(
            f"Generated {date_stamp} · {len(rows)} adjustments · "
            f"net delta {net:+,d} units"
        ),
        filename_stem="fulcrum-inventory-adjustments",
        empty_message="No inventory adjustments match the filters.",
        columns=[
            ReportColumn("timestamp",    "When",       formatter=fmt_date),
            ReportColumn("product_id",   "Product ID", align="right", formatter=fmt_int),
            ReportColumn("product_sku",  "SKU"),
            ReportColumn("product_name", "Product"),
            ReportColumn("adjustment",   "Delta",      align="right", formatter=fmt_int),
            ReportColumn("reason",       "Reason"),
            ReportColumn("created_by",   "Created by"),
        ],
        rows=rows,
    )


class InventoryAdjustmentRow(BaseModel):
    """One audit log entry returned by the JSON list endpoint. Mirrors the
    columns the CSV/PDF export emits so frontend and exports stay aligned."""
    id: int
    timestamp: Optional[datetime] = None
    product_id: Optional[int] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    adjustment: int
    reason: Optional[str] = None
    created_by: Optional[str] = None


class InventoryAdjustmentList(BaseModel):
    rows: List[InventoryAdjustmentRow]
    total: int
    """Total matching rows ignoring pagination. The frontend uses this to
    render a paginator without a second round-trip."""


@router.get("/inventory-adjustments", response_model=InventoryAdjustmentList)
def list_inventory_adjustments(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
):
    """Paginated audit log of every inventory quantity change. Newest first.
    Same filter shape as the CSV/PDF export endpoints so a buyer can find
    the rows on screen, then click Export to get the full filtered set."""
    from sqlalchemy.orm import joinedload as _joinedload

    base = db.query(InventoryAdjustment)
    if product_id is not None:
        base = base.filter(InventoryAdjustment.product_id == product_id)
    if after is not None:
        base = base.filter(InventoryAdjustment.timestamp >= after)
    if before is not None:
        base = base.filter(InventoryAdjustment.timestamp <= before)

    total = base.count()

    page_q = (
        base.options(_joinedload(InventoryAdjustment.product))
        .order_by(
            InventoryAdjustment.timestamp.desc().nullslast(),
            InventoryAdjustment.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    rows: list[InventoryAdjustmentRow] = []
    for adj in page_q.all():
        product = adj.product
        rows.append(
            InventoryAdjustmentRow(
                id=adj.id,
                timestamp=adj.timestamp or adj.created_at,
                product_id=adj.product_id,
                product_sku=product.sku if product else None,
                product_name=product.name if product else None,
                adjustment=adj.adjustment,
                reason=adj.reason,
                created_by=adj.created_by,
            )
        )
    return InventoryAdjustmentList(rows=rows, total=total)


@router.get("/inventory-adjustments/export")
def export_inventory_adjustments_csv(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the inventory-adjustment audit log as a CSV. Sorted newest
    first. Default limit is 5000 (cap 20000) for "give me the whole
    quarter" audit requests."""
    rows = _build_inventory_adjustment_rows(
        db, product_id=product_id, after=after, before=before, limit=limit,
    )
    return stream_csv(_inventory_adjustment_table(rows))


@router.get("/inventory-adjustments/export-pdf")
def export_inventory_adjustments_pdf(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the inventory-adjustment audit log as a printable PDF."""
    rows = _build_inventory_adjustment_rows(
        db, product_id=product_id, after=after, before=before, limit=limit,
    )
    return stream_pdf(_inventory_adjustment_table(rows))


# ---------------------------------------------------------------------------
# Shopping-cart-style reorder workflow
# ---------------------------------------------------------------------------

class ReorderRequest(BaseModel):
    product_ids: List[int]
    # Optional override of the suggested reorder qty, keyed by product_id.
    # Anything not in this map uses the report's suggestion logic.
    quantity_overrides: Optional[dict[int, int]] = None


class CreatedReorderPO(BaseModel):
    purchase_order_id: int
    supplier_id: int
    supplier_name: str
    product_count: int
    total_amount: float


class SkippedReorderProduct(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    reason: str  # "no_supplier" | "product_not_found"


class ReorderResponse(BaseModel):
    created_purchase_orders: List[CreatedReorderPO]
    skipped: List[SkippedReorderProduct]


@router.post("/low-stock/reorder", response_model=ReorderResponse)
def reorder_low_stock_products(
    *,
    db: Session = Depends(get_db),
    request: ReorderRequest,
    current_user: User = Depends(get_current_active_user),
) -> ReorderResponse:
    """
    Shopping-cart-style reorder: take a list of product_ids (typically
    selected on the low-stock widget) and create one DRAFT purchase order
    per primary supplier, with each selected product as a line item.

    Quantity per line:
      1. `quantity_overrides[product_id]` if provided
      2. `product.reorder_quantity` if set
      3. Velocity-based fallback: `max(30 * daily_velocity, threshold * 2)`
         — matches the suggestion logic in the low-stock report so the
         numbers the user just saw are the numbers they get.

    Supplier resolution:
      - Look up `SupplierProduct` rows for each product
      - Prefer the one marked `is_primary=True`; otherwise pick the
        most-recently-updated row (deterministic + matches existing
        product-supplier-manager behaviour)
      - Products with no supplier mapped are returned in the `skipped`
        list — we can't create a draft PO without a supplier, but we
        also don't want to silently drop them.

    Unit cost per line:
      - `supplier_product.cost_price` if non-zero, else
      - `product.cost_price` as a fallback (the product's own cost is
        usually the most recent purchase cost)

    Returns one `CreatedReorderPO` summary per PO created so the
    frontend can deep-link to each draft for review before the buyer
    sends it.
    """
    if not request.product_ids:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.purchaseOrder.reorderEmptySelection",
            detail="Select at least one product to reorder.",
        )

    overrides = request.quantity_overrides or {}

    # Pre-fetch everything we need in a few queries instead of N+1.
    products_by_id: dict[int, Product] = {
        p.id: p for p in db.query(Product).filter(Product.id.in_(request.product_ids)).all()
    }

    supplier_rows = (
        db.query(SupplierProduct)
        .filter(SupplierProduct.product_id.in_(request.product_ids))
        .all()
    )
    # Group supplier rows by product, preferring primary then most-recent
    primary_supplier_by_product: dict[int, SupplierProduct] = {}
    for sp in supplier_rows:
        existing = primary_supplier_by_product.get(sp.product_id)
        if existing is None:
            primary_supplier_by_product[sp.product_id] = sp
            continue
        # Replace if the new row is primary and existing isn't, or
        # if both/neither primary and new is more recent.
        new_pref = (sp.is_primary, sp.updated_at or sp.created_at)
        old_pref = (existing.is_primary, existing.updated_at or existing.created_at)
        if new_pref > old_pref:
            primary_supplier_by_product[sp.product_id] = sp

    # Settings + thresholds for the velocity-based fallback (mirror the
    # logic in low_stock_report so the cart numbers match what the user saw).
    settings = crud_store_settings.get_settings(db)
    store_default = (
        settings.low_stock_quantity_default
        if settings and settings.low_stock_quantity_default is not None
        else 10
    )
    pis_by_product = {
        row.product_id: row for row in db.query(ProductInventorySettings).all()
    }

    def _suggested_qty(product: Product) -> int:
        if product.id in overrides:
            return int(overrides[product.id])
        if product.reorder_quantity is not None:
            return int(product.reorder_quantity)
        pis = pis_by_product.get(product.id)
        threshold = int(
            product.reorder_point
            if product.reorder_point is not None
            else (
                pis.low_stock_quantity_threshold
                if pis and pis.low_stock_quantity_threshold is not None
                else store_default
            )
        )
        velocity = inventory_service.calculate_sales_velocity(db, product.id, days=30)
        velocity_suggestion = int(round(velocity * 30))
        floor_suggestion = max(threshold * 2, 1)
        return max(velocity_suggestion, floor_suggestion)

    # Group product_ids by the supplier we resolved.
    supplier_groups: dict[int, list[int]] = {}
    skipped: list[SkippedReorderProduct] = []
    for pid in request.product_ids:
        product = products_by_id.get(pid)
        if product is None:
            skipped.append(SkippedReorderProduct(
                product_id=pid, product_name=None, reason="product_not_found",
            ))
            continue
        sp = primary_supplier_by_product.get(pid)
        if sp is None:
            skipped.append(SkippedReorderProduct(
                product_id=pid, product_name=product.name, reason="no_supplier",
            ))
            continue
        supplier_groups.setdefault(sp.supplier_id, []).append(pid)

    created: list[CreatedReorderPO] = []
    for supplier_id, group_pids in supplier_groups.items():
        po = PurchaseOrder(
            supplier_id=supplier_id,
            status=PurchaseOrderStatus.DRAFT.value,
            notes="Auto-created from low-stock reorder cart",
            currency=(settings.default_currency if settings and getattr(settings, "default_currency", None) else "USD"),
        )
        db.add(po)
        db.flush()  # get po.id

        total_amount = 0.0
        for pid in group_pids:
            product = products_by_id[pid]
            sp = primary_supplier_by_product[pid]
            qty = _suggested_qty(product)
            unit_cost = float(sp.cost_price or 0.0) or float(product.cost_price or 0.0)
            db.add(PurchaseOrderItem(
                po_id=po.id,
                product_id=pid,
                quantity_ordered=qty,
                unit_cost=unit_cost,
                base_cost=unit_cost,
            ))
            total_amount += qty * unit_cost

        po.total_amount = total_amount
        db.add(po)
        db.flush()

        created.append(CreatedReorderPO(
            purchase_order_id=po.id,
            supplier_id=supplier_id,
            supplier_name=po.supplier.name if po.supplier else "",
            product_count=len(group_pids),
            total_amount=round(total_amount, 2),
        ))

    db.commit()

    return ReorderResponse(created_purchase_orders=created, skipped=skipped)


# ---------------------------------------------------------------------------
# Velocity / margin / stockout reports
#
# All three reports operate over a configurable window. By default they look
# at "last N days" (`window_days`, default 30, capped at 365) — back-compat
# with the original API. Optional `start_date` + `end_date` query params let
# operators pin an explicit calendar range ("last quarter") without having
# to do day-math. When either is set, it wins over `window_days`.
#
# They all share an aggregation pass over SalesOrderItem joined to SalesOrder
# filtered to status IN ("COMPLETED", "SHIPPED") — same filter
# `InventoryService.calculate_sales_velocity` uses, so the numbers line up
# with the low-stock report's `daily_velocity` column.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _DateWindow:
    """Resolved analytics window. `start_dt` and `end_dt` are inclusive
    UTC datetimes; `label` is the human-readable form rendered into the
    report subtitle ("window 30d" for the legacy path, "2026-01-01 →
    2026-03-31" for an explicit range)."""
    start_dt: datetime
    end_dt: datetime
    label: str

    @property
    def days(self) -> int:
        """Calendar-day span used for `daily_velocity` math. Floored at 1
        so a same-day range still divides cleanly."""
        return max(1, (self.end_dt - self.start_dt).days)


def _resolve_date_window(
    window_days: int,
    start_date: Optional[date],
    end_date: Optional[date],
) -> _DateWindow:
    """Convert the three competing window query params into a single
    `_DateWindow`. Rules:

      - When both / either of `start_date` and `end_date` are set, build
        an explicit range. `end_date` missing → "now". `start_date`
        missing → `end - window_days` (so an open-ended end-date "report
        through 2026-03-31" still has a sensible left bound).
      - When neither is set, fall back to `(now - window_days, now)`.
      - `start_date > end_date` is a 400 — the operator typoed.

    Both bounds are interpreted in UTC at midnight (`start`) and
    end-of-day (`end`), so a "2026-01-01 → 2026-01-01" range captures
    every order created on that calendar day.
    """
    if start_date is not None or end_date is not None:
        end_dt = (
            datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
            if end_date is not None
            else datetime.now(timezone.utc)
        )
        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        else:
            start_dt = end_dt - timedelta(days=window_days)
        if start_dt > end_dt:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.reports.invalidDateRange",
                params={"start": start_dt.date().isoformat(), "end": end_dt.date().isoformat()},
                detail="start_date must be on or before end_date",
            )
        label = f"{start_dt.date().isoformat()} → {end_dt.date().isoformat()}"
        return _DateWindow(start_dt=start_dt, end_dt=end_dt, label=label)

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=window_days)
    return _DateWindow(start_dt=start_dt, end_dt=end_dt, label=f"window {window_days}d")


# Status values that count as realized revenue. Matches
# inventory_service.calculate_sales_velocity, which is the contract callers
# already rely on. Kept as a module constant so all three new reports stay
# in sync if we change the set later (e.g. add "INVOICED").
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED")


def _sales_aggregates_by_product(
    db: Session, *, window: _DateWindow,
) -> dict[int, tuple[int, float]]:
    """One pass over SalesOrderItem joined to SalesOrder, grouped by product.

    Returns {product_id: (units_sold, revenue)} for every product that had a
    realized sale in the window. Used by both the velocity and margin
    reports — the stockout report only needs units_sold, so it reads the
    same map.

    Single grouped query > calling `calculate_sales_velocity` per product
    in a loop, because the velocity helper hits the DB once per product.
    The 2000-product cap on the snapshot report would otherwise be 2000
    queries on a full run.
    """
    rows = (
        db.query(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            func.coalesce(
                func.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit),
                0.0,
            ),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .filter(SalesOrder.created_at >= window.start_dt)
        .filter(SalesOrder.created_at <= window.end_dt)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .group_by(SalesOrderItem.product_id)
        .all()
    )
    return {pid: (int(units or 0), float(revenue or 0.0)) for pid, units, revenue in rows}


def _on_hand_by_product(db: Session) -> dict[int, int]:
    """Sum InventoryItem.quantity per product across all locations."""
    rows = (
        db.query(
            InventoryItem.product_id,
            func.coalesce(func.sum(InventoryItem.quantity), 0),
        )
        .group_by(InventoryItem.product_id)
        .all()
    )
    return {pid: int(qty or 0) for pid, qty in rows}


# ---- Velocity report ------------------------------------------------------


class VelocityRow(BaseModel):
    product_id: int
    product_sku: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    on_hand: int
    units_sold: int
    daily_velocity: float
    days_of_inventory: float


def _build_velocity_rows(
    db: Session, *, window: _DateWindow, limit: int,
) -> list[VelocityRow]:
    """Rank every non-bundle product by daily velocity over the window.

    Zero-sales products are included so the bottom of the list is
    auditable (a buyer can see "yes, these 40 SKUs sold nothing for 30
    days"). days_of_inventory == 999.0 marks the no-velocity case, same
    convention `inventory_service.calculate_days_of_inventory` uses.
    """
    sales = _sales_aggregates_by_product(db, window=window)
    on_hand_map = _on_hand_by_product(db)

    products = (
        db.query(Product)
        .filter(Product.is_bundle.is_(False))
        .order_by(Product.id.asc())
        .limit(2000)
        .all()
    )

    rows: list[VelocityRow] = []
    days = window.days
    for product in products:
        units, _revenue = sales.get(product.id, (0, 0.0))
        velocity = units / days if days else 0.0
        on_hand = on_hand_map.get(product.id, 0)
        if velocity > 0:
            days_left = round(on_hand / velocity, 1)
        else:
            days_left = 999.0
        rows.append(VelocityRow(
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            category=product.category,
            on_hand=on_hand,
            units_sold=units,
            daily_velocity=round(velocity, 2),
            days_of_inventory=days_left,
        ))

    # Top movers first; ties broken by units_sold then product_id so the
    # ordering stays deterministic across runs (matters for test stability
    # and for CSV diffs the buyer might do between snapshots).
    rows.sort(key=lambda r: (-r.daily_velocity, -r.units_sold, r.product_id))
    return rows[:limit]


def _velocity_table(rows: list[VelocityRow], *, window: _DateWindow) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_units = sum(r.units_sold for r in rows)
    return ReportTable(
        title="Fulcrum — Sales Velocity Report",
        subtitle=(
            f"Generated {date_stamp} · {window.label} · "
            f"{len(rows)} products · {total_units:,} units sold"
        ),
        filename_stem="fulcrum-velocity",
        empty_message="No products to report.",
        columns=[
            ReportColumn("product_id",        "Product ID"),
            ReportColumn("product_sku",       "SKU"),
            ReportColumn("product_name",      "Product"),
            ReportColumn("category",          "Category"),
            ReportColumn("on_hand",           "On hand",        align="right", formatter=fmt_int),
            ReportColumn("units_sold",        "Units sold",     align="right", formatter=fmt_int),
            ReportColumn("daily_velocity",    "Daily velocity", align="right", formatter=fmt_float(2)),
            ReportColumn("days_of_inventory", "Days left",      align="right", formatter=fmt_float(1)),
        ],
        rows=rows,
    )


@router.get("/velocity/export")
def export_velocity_csv(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product sales velocity over a configurable window as a CSV.

    Pass `start_date` / `end_date` (ISO 8601 dates, YYYY-MM-DD) to pin
    an explicit calendar range; otherwise the report covers the last
    `window_days` days ending now.
    """
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_velocity_rows(db, window=window, limit=limit)
    return stream_csv(_velocity_table(rows, window=window))


@router.get("/velocity/export-pdf")
def export_velocity_pdf(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product sales velocity over a configurable window as a PDF."""
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_velocity_rows(db, window=window, limit=limit)
    return stream_pdf(_velocity_table(rows, window=window))


# ---- Margin report --------------------------------------------------------


class MarginRow(BaseModel):
    product_id: int
    product_sku: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    units_sold: int
    revenue: float
    cost: float
    gross_margin: float
    margin_pct: float


def _build_margin_rows(
    db: Session, *, window: _DateWindow, limit: int,
) -> list[MarginRow]:
    """Per-product realized margin over the window.

    Only products with at least one realized sale show up — a zero row
    has no margin to report and would bloat the export.

    Cost basis precedence (per line, summed):
      1. `sales_order_items.cost_per_unit` — captured at order-create
         time. New default since migration 5d9f2a3b1c08.
      2. `products.cost_price` — current master cost. Used for legacy
         rows (cost_per_unit IS NULL) so reports over pre-migration
         windows still render. Drifts when master cost changes, which
         is the bug we're closing for new rows.

    Implemented with `SUM(quantity * COALESCE(items.cost_per_unit,
    products.cost_price))` so the mixed case (some lines captured,
    some legacy) sums correctly in a single query.
    """
    rows_raw = (
        db.query(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            func.coalesce(
                func.sum(SalesOrderItem.quantity * SalesOrderItem.price_per_unit),
                0.0,
            ),
            func.coalesce(
                func.sum(
                    SalesOrderItem.quantity
                    * func.coalesce(SalesOrderItem.cost_per_unit, Product.cost_price)
                ),
                0.0,
            ),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .join(Product, Product.id == SalesOrderItem.product_id)
        .filter(SalesOrder.created_at >= window.start_dt)
        .filter(SalesOrder.created_at <= window.end_dt)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .filter(Product.is_bundle.is_(False))
        .group_by(SalesOrderItem.product_id)
        .all()
    )
    if not rows_raw:
        return []

    product_ids = [pid for pid, _, _, _ in rows_raw]
    products_by_id = {
        p.id: p
        for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }

    rows: list[MarginRow] = []
    for pid, units_raw, revenue_raw, cost_raw in rows_raw:
        product = products_by_id.get(pid)
        if product is None:
            continue
        units = int(units_raw or 0)
        revenue = float(revenue_raw or 0.0)
        cost = float(cost_raw or 0.0)
        gross = revenue - cost
        margin_pct = (gross / revenue * 100.0) if revenue else 0.0
        rows.append(MarginRow(
            product_id=pid,
            product_sku=product.sku,
            product_name=product.name,
            category=product.category,
            units_sold=units,
            revenue=round(revenue, 2),
            cost=round(cost, 2),
            gross_margin=round(gross, 2),
            margin_pct=round(margin_pct, 2),
        ))

    rows.sort(key=lambda r: (-r.gross_margin, -r.revenue, r.product_id))
    return rows[:limit]


def _margin_table(rows: list[MarginRow], *, window: _DateWindow) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_revenue = sum(r.revenue for r in rows)
    total_margin = sum(r.gross_margin for r in rows)
    return ReportTable(
        title="Fulcrum — Gross Margin Report",
        subtitle=(
            f"Generated {date_stamp} · {window.label} · "
            f"{len(rows)} products · revenue ${total_revenue:,.2f} · "
            f"margin ${total_margin:,.2f}"
        ),
        filename_stem="fulcrum-margin",
        empty_message="No realized sales in the selected window.",
        columns=[
            ReportColumn("product_id",   "Product ID"),
            ReportColumn("product_sku",  "SKU"),
            ReportColumn("product_name", "Product"),
            ReportColumn("category",     "Category"),
            ReportColumn("units_sold",   "Units sold",   align="right", formatter=fmt_int),
            ReportColumn("revenue",      "Revenue",      align="right", formatter=fmt_currency),
            ReportColumn("cost",         "Cost",         align="right", formatter=fmt_currency),
            ReportColumn("gross_margin", "Gross margin", align="right", formatter=fmt_currency),
            ReportColumn("margin_pct",   "Margin %",     align="right", formatter=fmt_percent),
        ],
        rows=rows,
    )


@router.get("/margin/export")
def export_margin_csv(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product realized gross margin over a window as a CSV."""
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_margin_rows(db, window=window, limit=limit)
    return stream_csv(_margin_table(rows, window=window))


@router.get("/margin/export-pdf")
def export_margin_pdf(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-product realized gross margin over a window as a PDF."""
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_margin_rows(db, window=window, limit=limit)
    return stream_pdf(_margin_table(rows, window=window))


# ---- Stockout report ------------------------------------------------------


class StockoutRow(BaseModel):
    product_id: int
    product_sku: Optional[str] = None
    product_name: str
    on_hand: int
    daily_velocity: float
    days_of_inventory: float
    severity: str  # "out" (on_hand==0) | "imminent" (<7d) | "watch" (<14d)


_STOCKOUT_SEVERITY_BG = {
    "out":      "#fde7e7",  # light red — matches low-stock "critical"
    "imminent": "#fff4d6",  # light amber
    "watch":    "#f0f4ff",  # light blue
}


def _build_stockout_rows(
    db: Session,
    *,
    window: _DateWindow,
    imminent_days: int,
    watch_days: int,
    limit: int,
) -> list[StockoutRow]:
    """Products that are already stocked-out or projected to be.

    Distinct from low-stock: low-stock is threshold-based (current qty
    vs reorder point); this report is velocity-based (when will the
    current qty run out?). A product can be well above its threshold
    today but still flagged here if sales velocity is high enough to
    drain stock before the next planned reorder cycle.

    Severity tiers:
      - "out"      — on_hand == 0 now
      - "imminent" — days_of_inventory <= imminent_days (default 7)
      - "watch"    — days_of_inventory <= watch_days (default 14)
    Products with more days of inventory than `watch_days` are excluded.
    """
    sales = _sales_aggregates_by_product(db, window=window)
    on_hand_map = _on_hand_by_product(db)

    products = (
        db.query(Product)
        .filter(Product.is_bundle.is_(False))
        .order_by(Product.id.asc())
        .limit(2000)
        .all()
    )

    rows: list[StockoutRow] = []
    days = window.days
    for product in products:
        units, _revenue = sales.get(product.id, (0, 0.0))
        on_hand = on_hand_map.get(product.id, 0)
        velocity = units / days if days else 0.0
        if velocity > 0:
            days_left = round(on_hand / velocity, 1)
        else:
            days_left = 999.0

        if on_hand <= 0:
            severity = "out"
        elif days_left <= imminent_days:
            severity = "imminent"
        elif days_left <= watch_days:
            severity = "watch"
        else:
            continue  # plenty of cover — skip

        rows.append(StockoutRow(
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            on_hand=on_hand,
            daily_velocity=round(velocity, 2),
            days_of_inventory=days_left,
            severity=severity,
        ))

    severity_order = {"out": 0, "imminent": 1, "watch": 2}
    rows.sort(key=lambda r: (severity_order[r.severity], r.days_of_inventory, r.product_id))
    return rows[:limit]


def _stockout_table(
    rows: list[StockoutRow],
    *,
    window: _DateWindow,
    imminent_days: int,
    watch_days: int,
) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_count = sum(1 for r in rows if r.severity == "out")
    imm_count = sum(1 for r in rows if r.severity == "imminent")
    watch_count = sum(1 for r in rows if r.severity == "watch")
    return ReportTable(
        title="Fulcrum — Projected Stockout Report",
        subtitle=(
            f"Generated {date_stamp} · velocity {window.label} · "
            f"imminent ≤{imminent_days}d · watch ≤{watch_days}d · "
            f"{out_count} out · {imm_count} imminent · {watch_count} watch"
        ),
        filename_stem="fulcrum-stockout",
        empty_message="No products are currently stocked-out or at risk.",
        columns=[
            ReportColumn("product_id",        "Product ID"),
            ReportColumn("product_sku",       "SKU"),
            ReportColumn("product_name",      "Product"),
            ReportColumn("severity",          "Severity"),
            ReportColumn("on_hand",           "On hand",        align="right", formatter=fmt_int),
            ReportColumn("daily_velocity",    "Daily velocity", align="right", formatter=fmt_float(2)),
            ReportColumn("days_of_inventory", "Days left",      align="right", formatter=fmt_float(1)),
        ],
        rows=rows,
        row_style=lambda row: (
            {"background": _STOCKOUT_SEVERITY_BG[row.severity]}
            if row.severity in _STOCKOUT_SEVERITY_BG else None
        ),
    )


@router.get("/stockout/export")
def export_stockout_csv(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    imminent_days: int = Query(7, ge=1, le=90),
    watch_days: int = Query(14, ge=1, le=180),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Projected-stockout report as a CSV. Velocity-based, distinct from
    the threshold-based low-stock report."""
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_stockout_rows(
        db, window=window, imminent_days=imminent_days,
        watch_days=watch_days, limit=limit,
    )
    return stream_csv(_stockout_table(
        rows, window=window,
        imminent_days=imminent_days, watch_days=watch_days,
    ))


@router.get("/stockout/export-pdf")
def export_stockout_pdf(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None, description="Inclusive lower bound (UTC). Overrides window_days when set."),
    end_date: Optional[date] = Query(None, description="Inclusive upper bound (UTC). Overrides window_days when set."),
    imminent_days: int = Query(7, ge=1, le=90),
    watch_days: int = Query(14, ge=1, le=180),
    limit: int = Query(2000, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Projected-stockout report as a printable PDF, severity-colored."""
    window = _resolve_date_window(window_days, start_date, end_date)
    rows = _build_stockout_rows(
        db, window=window, imminent_days=imminent_days,
        watch_days=watch_days, limit=limit,
    )
    return stream_pdf(_stockout_table(
        rows, window=window,
        imminent_days=imminent_days, watch_days=watch_days,
    ))


# ---- Cost rollup (Phase 8 Track 1) -----------------------------------------


class CostRollupResponse(BaseModel):
    """Aggregate net-margin rollup over a window. Sets up Track 2's
    dashboard charts — frontend can consume this to plot "today's
    profit" or "margin vs. spend" without re-implementing the cost
    formula client-side.
    """
    window_days: int
    source: Optional[str] = None
    orders: int
    revenue_amount_mxn: float
    cogs_amount: float
    marketplace_fees_amount: float
    shipping_cost_amount: float
    ad_spend_amount: float
    other_cost_amount: float
    total_cost_amount: float
    net_profit_amount: float
    net_margin_percent: Optional[float] = None


@router.get("/cost-rollup", response_model=CostRollupResponse)
def cost_rollup_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    source: Optional[str] = Query(
        None,
        description=(
            "Optional channel filter: amazon / mercadolibre / fulcrum. "
            "Lowercase or mixed case. Omit for cross-channel rollup."
        ),
    ),
    current_user: User = Depends(get_current_active_user),
) -> CostRollupResponse:
    """Aggregate net-margin rollup over the last N days.

    Pulls from the `order_cost_breakdowns` table populated by the
    cost engine. Restricts to realized order statuses
    (COMPLETED/SHIPPED/DELIVERED/PAID) so cancelled and pending
    orders don't pollute the headline margin number.
    """
    from src.models.order import OrderSource
    from src.services.order_cost_engine import aggregate_rollup

    parsed_source: Optional[OrderSource] = None
    if source:
        try:
            parsed_source = OrderSource(source.upper())
        except ValueError:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.report.unknownSource",
                params={"source": source},
                detail=f"Unknown source '{source}'",
            )

    rollup = aggregate_rollup(db, window_days=window_days, source=parsed_source)
    return CostRollupResponse(
        window_days=window_days,
        source=parsed_source.value if parsed_source else None,
        **rollup,
    )


# ---- Cost rollup: per-channel (Track 2 stacked bar) -----------------------


class CostRollupByChannelRow(BaseModel):
    """One row per channel that had realized orders in the window."""
    source: str
    orders: int
    revenue_amount_mxn: float
    cogs_amount: float
    marketplace_fees_amount: float
    shipping_cost_amount: float
    ad_spend_amount: float
    other_cost_amount: float
    total_cost_amount: float
    net_profit_amount: float
    net_margin_percent: Optional[float] = None


class CostRollupByChannelResponse(BaseModel):
    window_days: int
    channels: List[CostRollupByChannelRow]


@router.get(
    "/cost-rollup/by-channel",
    response_model=CostRollupByChannelResponse,
)
def cost_rollup_by_channel(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> CostRollupByChannelResponse:
    """Per-channel net-margin rollup. Powers the dashboard's
    "Margin by channel" stacked bar chart — one stack per source
    showing the COGS / fees / shipping / profit breakdown.

    Channels with zero orders in the window are omitted so the chart
    doesn't render an empty bar that the operator has to mentally
    discount.
    """
    from src.services.order_cost_engine import aggregate_rollup_by_channel

    rows = aggregate_rollup_by_channel(db, window_days=window_days)
    return CostRollupByChannelResponse(
        window_days=window_days,
        channels=[CostRollupByChannelRow(**row) for row in rows],
    )


# ---- Cost rollup: daily time-series (Track 2 line chart) ------------------


class CostRollupDailyRow(BaseModel):
    """One row per calendar day in the window. Days with zero orders
    appear with zero values so the time-series renders a continuous
    line."""
    date: str  # ISO YYYY-MM-DD
    orders: int
    revenue_amount_mxn: float
    total_cost_amount: float
    net_profit_amount: float


class CostRollupDailyResponse(BaseModel):
    window_days: int
    series: List[CostRollupDailyRow]


@router.get(
    "/cost-rollup/daily",
    response_model=CostRollupDailyResponse,
)
def cost_rollup_daily(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> CostRollupDailyResponse:
    """Daily revenue / total-cost / net-profit time-series. Powers
    the dashboard's "Sales vs spend" line chart. Days with zero
    orders are emitted with zero values so the chart's x-axis
    stays continuous — otherwise the line would have visible gaps
    on quiet days."""
    from src.services.order_cost_engine import aggregate_daily_series

    series = aggregate_daily_series(db, window_days=window_days)
    return CostRollupDailyResponse(
        window_days=window_days,
        series=[CostRollupDailyRow(**row) for row in series],
    )


# ---- Top movers (Track 2 leaderboard) ------------------------------------


class TopMoverRow(BaseModel):
    product_id: int
    name: Optional[str] = None
    sku: Optional[str] = None
    units: int
    revenue_amount: float
    cogs_amount: float
    overhead_amount: float  # marketplace fees + shipping + ads, pro-rated
    total_cost_amount: float
    net_profit_amount: float
    net_margin_percent: Optional[float] = None


class TopMoversResponse(BaseModel):
    window_days: int
    limit: int
    rows: List[TopMoverRow]


@router.get("/top-movers", response_model=TopMoversResponse)
def top_movers_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
) -> TopMoversResponse:
    """Top N products by revenue over the window. Each row carries
    per-product net margin — order-level fees + shipping are pro-
    rated by each product's revenue share of its parent order so
    the per-product net profit reflects the true contribution to
    the headline rollup."""
    from src.services.order_cost_engine import top_movers

    rows = top_movers(db, window_days=window_days, limit=limit)
    return TopMoversResponse(
        window_days=window_days,
        limit=limit,
        rows=[TopMoverRow(**row) for row in rows],
    )


# ---- Dead stock (Track 2 follow-up) ---------------------------------------
#
# "Dead stock" = products with on-hand inventory but near-zero recent sales
# velocity. Operator scans this to identify SKUs to discount, bundle, stop
# reordering, or eventually write off.
#
# Implementation note on the velocity threshold: defaults to 0.1 units/day,
# i.e. < 1 sale per 10 days. The threshold is configurable per request so
# operators can tune it for their channel mix (an Amazon-Mexico seller might
# call 0.05/day dead; an ML-Full seller with higher SKU velocity might use
# 0.5/day). Frontend default is 0.1 to match.


class DeadStockRow(BaseModel):
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    on_hand: int
    units_sold: int
    daily_velocity: float
    # Calendar days since the product's most-recent realized sale.
    # None when the product has NEVER sold (existed long enough to
    # qualify for dead-stock but no realized order line has ever
    # referenced it). Sorted to the top of the list because never-
    # sold inventory is the worst kind.
    days_since_last_sale: Optional[int] = None
    cost_price: Optional[float] = None
    # On-hand qty × current cost_price — the dollars "frozen" in this
    # SKU. Lets the operator triage by capital at risk, not just unit
    # count.
    stock_value_at_cost: Optional[float] = None


class DeadStockResponse(BaseModel):
    window_days: int
    threshold_daily_velocity: float
    rows: List[DeadStockRow]


def _build_dead_stock_rows(
    db: Session,
    *,
    window_days: int,
    threshold_daily_velocity: float,
    limit: int,
) -> List[DeadStockRow]:
    """Per-product dead-stock candidates over the window.

    Filter:
      - on_hand > 0 (zero-stock products aren't "dead", they're
        out — the stockout report handles those).
      - daily_velocity <= threshold.
      - is_bundle = False (bundles are virtual; the underlying
        component products carry the real stock).

    Order: never-sold first (days_since_last_sale IS NULL), then by
    days_since_last_sale desc (longest-dead first), then by
    stock_value_at_cost desc. The capital-at-risk tiebreaker lets
    the operator's eye land on $-heavy SKUs faster.
    """
    window = _resolve_date_window(window_days, None, None)
    units_by_product = _sales_aggregates_by_product(db, window=window)
    on_hand_by_product = _on_hand_by_product(db)

    # Last-sale lookup: max(SalesOrder.created_at) joined through
    # SalesOrderItem.product_id for realized orders only. We grab
    # every product (not just window-scoped) so a SKU dead for 6
    # months in a 30-day window still shows its real last-sale age.
    last_sale_rows = (
        db.query(
            SalesOrderItem.product_id,
            func.max(SalesOrder.created_at),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .group_by(SalesOrderItem.product_id)
        .all()
    )
    last_sale_by_product = {pid: ts for pid, ts in last_sale_rows}

    candidate_ids = list(on_hand_by_product.keys())
    if not candidate_ids:
        return []

    products = (
        db.query(Product)
        .filter(Product.id.in_(candidate_ids))
        .filter(Product.is_bundle.is_(False))
        .all()
    )

    today = datetime.utcnow().date()
    rows: List[DeadStockRow] = []
    for product in products:
        on_hand = int(on_hand_by_product.get(product.id, 0) or 0)
        if on_hand <= 0:
            continue
        units, _revenue = units_by_product.get(product.id, (0, 0.0))
        velocity = float(units) / float(window_days) if window_days > 0 else 0.0
        if velocity > threshold_daily_velocity:
            continue

        last_sale = last_sale_by_product.get(product.id)
        days_since_last_sale: Optional[int] = None
        if last_sale is not None:
            last_date = (
                last_sale.date() if hasattr(last_sale, "date") else last_sale
            )
            days_since_last_sale = max(0, (today - last_date).days)

        cost_price = (
            float(product.cost_price) if product.cost_price is not None else None
        )
        value = (
            round(on_hand * cost_price, 4) if cost_price is not None else None
        )

        rows.append(DeadStockRow(
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            on_hand=on_hand,
            units_sold=int(units),
            daily_velocity=round(velocity, 4),
            days_since_last_sale=days_since_last_sale,
            cost_price=cost_price,
            stock_value_at_cost=value,
        ))

    # Never-sold first (None sorts as "infinitely dead"), then by
    # days desc, then by stock value desc.
    rows.sort(key=lambda r: (
        0 if r.days_since_last_sale is None else 1,
        -(r.days_since_last_sale or 0),
        -(r.stock_value_at_cost or 0.0),
    ))
    return rows[:limit]


@router.get("/dead-stock", response_model=DeadStockResponse)
def dead_stock_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    threshold_daily_velocity: float = Query(
        0.1, ge=0.0, le=10.0,
        description=(
            "Daily velocity ceiling for inclusion (units/day). 0.1 ≈ <1 "
            "sale every 10 days. Tune per channel mix."
        ),
    ),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
) -> DeadStockResponse:
    """Products with on-hand inventory but near-zero recent sales
    velocity. The dashboard's dead-stock widget surfaces this so
    the operator can discount, bundle, or stop reordering before
    capital sits idle.
    """
    rows = _build_dead_stock_rows(
        db,
        window_days=window_days,
        threshold_daily_velocity=threshold_daily_velocity,
        limit=limit,
    )
    return DeadStockResponse(
        window_days=window_days,
        threshold_daily_velocity=threshold_daily_velocity,
        rows=rows,
    )


# ---- Refunds summary ------------------------------------------------------
#
# Surface marketplace-side refunds + cancellations as a single rolled-up
# count per channel. Two data sources:
#
#   1. `sales_order_status_events` — every transition `realized →
#      non-realized` represents an order moving into a refund / cancel
#      state. Counts these as full-order refunds.
#   2. `amazon_order_refunds` — Amazon partial refunds, where the order
#      stays Shipped but the buyer got money back for some lines.
#
# Both sources sum into the per-channel totals. Rate denominator is the
# count of realized orders created in the same window — same cutoff for
# both numerator and denominator so a 30d window gives a sensible
# 30d-rolling rate.


class RefundsByChannelRow(BaseModel):
    """One row per source. `refund_rate_percent` is the count of
    refunds divided by realized-orders-in-window, expressed as a
    percentage. NULL when no orders existed in the window (avoid
    divide-by-zero / 0%-of-0 misleading the operator)."""
    source: str
    refunds_count: int
    refunded_amount_mxn: float
    realized_orders_count: int
    refund_rate_percent: Optional[float] = None


class RefundsSummaryResponse(BaseModel):
    """Cross-channel rollup. The `label` mirrors what the velocity /
    margin / stockout endpoints render in their subtitle line so the
    dashboard widget can reuse the same wording ('window 30d' vs.
    '2026-01-01 → 2026-03-31')."""
    window_label: str
    totals: RefundsByChannelRow
    by_channel: List[RefundsByChannelRow]


@router.get("/refunds-summary", response_model=RefundsSummaryResponse)
def refunds_summary_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None,
        description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    current_user: User = Depends(get_current_active_user),
) -> RefundsSummaryResponse:
    """Per-channel refund + cancellation rollup over the window.

    Counts every status transition out of the realized set
    (full-order refund or cancellation) plus every Amazon partial-
    refund event posted in the window. The denominator for the rate
    is realized orders created in the same window — close enough for
    a rolling-rate signal at the dashboard level.
    """
    from src.models.order import (
        AmazonOrderRefund,
        OrderCostBreakdown,
        OrderSource,
        SalesOrder,
        SalesOrderStatusEvent,
    )
    from src.services.order_lifecycle import REALIZED_STATUSES

    window = _resolve_date_window(window_days, start_date, end_date)

    # --- 1. Full-order refunds: transitions out of realized.
    transitions = (
        db.query(SalesOrder.source, SalesOrderStatusEvent.order_id)
        .join(SalesOrder, SalesOrder.id == SalesOrderStatusEvent.order_id)
        .filter(SalesOrderStatusEvent.changed_at >= window.start_dt)
        .filter(SalesOrderStatusEvent.changed_at <= window.end_dt)
        .filter(SalesOrderStatusEvent.from_status.in_(REALIZED_STATUSES))
        .filter(SalesOrderStatusEvent.to_status.notin_(REALIZED_STATUSES))
        .all()
    )
    # Dedup by (source, order_id) so an order that bounced
    # realized→cancelled→realized→cancelled in-window counts once.
    refunded_orders: Dict[OrderSource, set] = {}
    for source, oid in transitions:
        refunded_orders.setdefault(source, set()).add(oid)

    # --- 2. Refund amounts for full-order refunds: revenue from breakdown.
    refund_revenue_mxn: Dict[OrderSource, float] = {}
    if any(refunded_orders.values()):
        all_oids: List[int] = [
            oid for oids in refunded_orders.values() for oid in oids
        ]
        rev_rows = (
            db.query(SalesOrder.source, OrderCostBreakdown.revenue_amount_mxn)
            .join(OrderCostBreakdown, OrderCostBreakdown.order_id == SalesOrder.id)
            .filter(SalesOrder.id.in_(all_oids))
            .all()
        )
        for source, rev in rev_rows:
            refund_revenue_mxn[source] = (
                refund_revenue_mxn.get(source, 0.0) + float(rev or 0.0)
            )

    # --- 3. Amazon partial refunds posted in the window.
    partial_rows = (
        db.query(AmazonOrderRefund.refund_amount)
        .filter(AmazonOrderRefund.posted_at.isnot(None))
        .filter(AmazonOrderRefund.posted_at >= window.start_dt)
        .filter(AmazonOrderRefund.posted_at <= window.end_dt)
        .all()
    )
    partial_count = len(partial_rows)
    partial_amount = sum(float(r.refund_amount or 0.0) for r in partial_rows)

    # --- 4. Denominator: realized orders created in window per source.
    denom_rows = (
        db.query(SalesOrder.source, func.count(SalesOrder.id))
        .filter(SalesOrder.created_at >= window.start_dt)
        .filter(SalesOrder.created_at <= window.end_dt)
        .filter(SalesOrder.status.in_(REALIZED_STATUSES))
        .group_by(SalesOrder.source)
        .all()
    )
    realized_by_source: Dict[OrderSource, int] = {s: int(c) for s, c in denom_rows}

    # --- 5. Build per-channel rows. Include every source the operator
    # would expect to see — even with zero refunds + zero orders — so
    # the dashboard widget renders a stable layout.
    by_channel: List[RefundsByChannelRow] = []
    for source in OrderSource:
        full_orders = refunded_orders.get(source, set())
        full_count = len(full_orders)
        full_amount = refund_revenue_mxn.get(source, 0.0)
        # Amazon partial refunds attribute to AMAZON only.
        if source == OrderSource.AMAZON:
            refunds_count = full_count + partial_count
            refunded_mxn = full_amount + partial_amount
        else:
            refunds_count = full_count
            refunded_mxn = full_amount

        realized_count = realized_by_source.get(source, 0)
        rate: Optional[float] = None
        if realized_count > 0:
            rate = round((refunds_count / realized_count) * 100.0, 2)

        by_channel.append(RefundsByChannelRow(
            source=source.value,
            refunds_count=refunds_count,
            refunded_amount_mxn=round(refunded_mxn, 2),
            realized_orders_count=realized_count,
            refund_rate_percent=rate,
        ))

    # --- 6. Cross-channel totals.
    total_refunds = sum(r.refunds_count for r in by_channel)
    total_refunded = sum(r.refunded_amount_mxn for r in by_channel)
    total_realized = sum(r.realized_orders_count for r in by_channel)
    total_rate: Optional[float] = None
    if total_realized > 0:
        total_rate = round((total_refunds / total_realized) * 100.0, 2)
    totals = RefundsByChannelRow(
        source="ALL",
        refunds_count=total_refunds,
        refunded_amount_mxn=round(total_refunded, 2),
        realized_orders_count=total_realized,
        refund_rate_percent=total_rate,
    )

    return RefundsSummaryResponse(
        window_label=window.label,
        totals=totals,
        by_channel=by_channel,
    )
