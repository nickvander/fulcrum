"""
Operational reports surface. Exposes the low-stock report used by the
dashboard widget plus reusable export endpoints (CSV + PDF) that all share
the same `report_export` helpers — see `src/services/report_export.py`.
"""
import math
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
from src.models.stock_transfer import LOCATION_INTERNAL, LOCATION_ML_FULL
from src.services import marketplace_catalog
from src.models.supplier_product import SupplierProduct
from src.models.user import User
from src.schemas.replenishment import ReplenishmentReport
from src.schemas.repricing import (
    ApplyPriceRequest,
    ApplyPriceResponse,
    RepricingReport,
)
from src.schemas.cfdi import CfdiReport
from src.services import cfdi_service, replenishment_service, repricing_service
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
    # Per-location split of `on_hand` so the UI can pick the right remedy:
    #   internal_on_hand > 0  → there is warehouse stock to *transfer* to Full
    #                           ("Enviar a ML Full")
    #   internal_on_hand == 0 → out of own stock → must *reorder* from the
    #                           supplier ("Crear OC").
    # `internal_on_hand` is the well-known "default" warehouse location and
    # `ml_full_on_hand` is the "ml-full" fulfillment-centre location. Any
    # other locations still roll up into `on_hand` but are not split out.
    internal_on_hand: int = 0
    ml_full_on_hand: int = 0
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

    # Group by (product, location) so we can both total on-hand *and* split
    # out the warehouse vs ML-Full buckets that the UI uses to choose the
    # right remedy (transfer existing stock vs reorder from supplier).
    on_hand_rows = (
        db.query(
            InventoryItem.product_id,
            InventoryItem.location,
            func.coalesce(func.sum(InventoryItem.quantity), 0).label("on_hand"),
        )
        .group_by(InventoryItem.product_id, InventoryItem.location)
        .all()
    )
    on_hand_by_product: Dict[int, int] = {}
    internal_by_product: Dict[int, int] = {}
    ml_full_by_product: Dict[int, int] = {}
    for pid, location, qty in on_hand_rows:
        qty = int(qty or 0)
        on_hand_by_product[pid] = on_hand_by_product.get(pid, 0) + qty
        if location == LOCATION_INTERNAL:
            internal_by_product[pid] = internal_by_product.get(pid, 0) + qty
        elif location == LOCATION_ML_FULL:
            ml_full_by_product[pid] = ml_full_by_product.get(pid, 0) + qty

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
                internal_on_hand=internal_by_product.get(product.id, 0),
                ml_full_on_hand=ml_full_by_product.get(product.id, 0),
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
# Replenishment-to-Full planner (B4) — adds the "when" the low-stock report
# lacks: dated "reorder by" / "send to Full by" actions across the two-stage
# Mexico supply chain (supplier -> internal -> ML Full). Computation lives in
# `services/replenishment_service.py`; this surface is the API + exports.
# ---------------------------------------------------------------------------


@router.get("/replenishment", response_model=ReplenishmentReport)
def replenishment_report(
    *,
    db: Session = Depends(get_db),
    velocity_window_days: int = Query(30, ge=1, le=365),
    full_transfer_lead_days: int = Query(14, ge=0, le=180),
    target_cover_days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> ReplenishmentReport:
    """Per-SKU replenishment plan for MercadoLibre-Full sellers.

    For each SKU selling on ML, returns the two dated actions needed to keep
    Full stocked: when to **send internal stock to Full** and when to
    **reorder from the supplier** (using `SupplierProduct.lead_time_days`).
    Velocity is ML-channel-scoped, matching the `ml_full_stockout_risk`
    alert. SKUs with no ML velocity, or with comfortable cover on both
    stages, are omitted.
    """
    return replenishment_service.build_replenishment_plan(
        db,
        velocity_window_days=velocity_window_days,
        full_transfer_lead_days=full_transfer_lead_days,
        target_cover_days=target_cover_days,
        limit=limit,
    )


_REPLENISHMENT_SEVERITY_BG = {
    "critical": "#fde7e7",  # light red — out of Full now
    "soon":     "#fff4d6",  # light amber — action due today
    "watch":    "#f0f4ff",  # light blue — action due within a week
}


def _replenishment_table(report: ReplenishmentReport) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ReportTable(
        title="Fulcrum — Replenishment-to-Full Plan",
        subtitle=(
            f"Generated {date_stamp} · {report.total_send_now} to send now · "
            f"{report.total_reorder_now} to reorder now · "
            f"{report.full_transfer_lead_days}d Full lead · "
            f"{report.target_cover_days}d target cover"
        ),
        filename_stem="fulcrum-replenishment",
        empty_message="No SKUs need replenishment action.",
        columns=[
            ReportColumn("product_id",          "Product ID"),
            ReportColumn("product_sku",         "SKU"),
            ReportColumn("product_name",        "Product"),
            ReportColumn("severity",            "Severity"),
            ReportColumn("daily_velocity",      "ML velocity",   align="right", formatter=fmt_float(2)),
            ReportColumn("internal_on_hand",    "Internal",      align="right", formatter=fmt_int),
            ReportColumn("full_available",      "Full avail.",   align="right", formatter=fmt_int),
            ReportColumn("days_cover_full",     "Full cover (d)", align="right", formatter=fmt_float(1)),
            ReportColumn("send_to_full_qty",    "Send to Full",  align="right", formatter=fmt_int),
            ReportColumn("send_to_full_by",     "Send by",       align="right", formatter=fmt_date),
            ReportColumn("reorder_qty",         "Reorder qty",   align="right", formatter=fmt_int),
            ReportColumn("reorder_by",          "Reorder by",    align="right", formatter=fmt_date),
        ],
        rows=report.rows,
        row_style=lambda row: (
            {"background": _REPLENISHMENT_SEVERITY_BG[row.severity]}
            if row.severity in _REPLENISHMENT_SEVERITY_BG
            else None
        ),
    )


@router.get("/replenishment/export")
def export_replenishment_csv(
    *,
    db: Session = Depends(get_db),
    velocity_window_days: int = Query(30, ge=1, le=365),
    full_transfer_lead_days: int = Query(14, ge=0, le=180),
    target_cover_days: int = Query(30, ge=1, le=365),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the replenishment plan as a CSV download."""
    report = replenishment_service.build_replenishment_plan(
        db,
        velocity_window_days=velocity_window_days,
        full_transfer_lead_days=full_transfer_lead_days,
        target_cover_days=target_cover_days,
        limit=limit,
    )
    return stream_csv(_replenishment_table(report))


@router.get("/replenishment/export-pdf")
def export_replenishment_pdf(
    *,
    db: Session = Depends(get_db),
    velocity_window_days: int = Query(30, ge=1, le=365),
    full_transfer_lead_days: int = Query(14, ge=0, le=180),
    target_cover_days: int = Query(30, ge=1, le=365),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Render the replenishment plan as a printable, severity-colored PDF."""
    report = replenishment_service.build_replenishment_plan(
        db,
        velocity_window_days=velocity_window_days,
        full_transfer_lead_days=full_transfer_lead_days,
        target_cover_days=target_cover_days,
        limit=limit,
    )
    return stream_pdf(_replenishment_table(report))


# ---------------------------------------------------------------------------
# Repricing assistant (B6) — margin-floor guard. Flags listings priced below
# a target net margin (using real settled fees + COGS) and pushes an approved
# price via the existing connector `sync_price`. Computation lives in
# `services/repricing_service.py`.
# ---------------------------------------------------------------------------


@router.get("/repricing", response_model=RepricingReport)
def repricing_report(
    *,
    db: Session = Depends(get_db),
    margin_floor_percent: float = Query(10.0, ge=0.0, le=95.0),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> RepricingReport:
    """Listings priced below a target net-margin floor.

    For each marketplace listing, computes the price needed to hit
    `margin_floor_percent` using the SKU's COGS plus its effective fee +
    shipping rate (from settled marketplace finance data when available,
    else the marketplace's default fee config). Returns only at-risk
    listings — selling at a loss, under the floor, or infeasible at the
    current fee rate.
    """
    return repricing_service.build_repricing_report(
        db,
        margin_floor_percent=margin_floor_percent / 100.0,
        limit=limit,
    )


@router.post("/repricing/apply", response_model=ApplyPriceResponse)
def apply_repricing(
    *,
    db: Session = Depends(get_db),
    payload: ApplyPriceRequest,
    current_user: User = Depends(get_current_active_user),
) -> ApplyPriceResponse:
    """Push an approved price to the marketplace and persist it on the
    listing. An expired token surfaces a 409 with a machine-readable `code`
    so the UI can show an inline Reconnect affordance (mirrors the Q&A
    answer endpoint)."""
    result = repricing_service.apply_price(
        db, listing_id=payload.listing_id, price=payload.price, user_id=current_user.id,
    )
    err = result.get("error")
    if err == "invalid_price":
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.repricing.invalidPrice",
            detail="Price must be greater than zero.",
        )
    if err == "not_found":
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.repricing.listingNotFound",
            params={"id": payload.listing_id},
            detail=f"Listing {payload.listing_id} not found or has no marketplace id.",
        )
    if err == "no_credentials":
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.repricing.noCredentials",
            detail="No marketplace credentials found to push the price.",
        )
    if err == "needs_reauthorization":
        raise LocalizedHTTPException(
            status_code=409,
            code="needs_reauthorization",
            detail="Marketplace authorization expired; reconnect to push prices.",
        )
    if err == "unsupported":
        raise LocalizedHTTPException(
            status_code=502,
            code="apiErrors.repricing.unsupported",
            detail="Price sync was rejected by the marketplace.",
        )
    if err:
        raise LocalizedHTTPException(
            status_code=500,
            code="apiErrors.repricing.applyFailed",
            detail="Failed to push the price to the marketplace.",
        )

    listing = result["listing"]
    return ApplyPriceResponse(
        listing_id=listing.id,
        marketplace_price=float(listing.marketplace_price or 0.0),
    )


# ---------------------------------------------------------------------------
# SAT/CFDI factura export (B7) — export-only. Emits realized sales in a
# CFDI 4.0-ready shape (público-general) for an accountant / PAC to timbrar.
# Computation lives in `services/cfdi_service.py`.
# ---------------------------------------------------------------------------


def _cfdi_date_range(
    start_date: Optional[str], end_date: Optional[str]
) -> tuple[Optional[date], Optional[date]]:
    """Parse ISO date strings; default to the last 30 days when neither is
    given so the export doesn't dump the entire order history by accident."""
    def _parse(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.report.invalidDate",
                params={"value": value},
                detail=f"Invalid date: {value}",
            )

    start = _parse(start_date)
    end = _parse(end_date)
    # Fill each bound independently so passing only one side never leaves
    # the other unbounded (which would dump the whole order history).
    if end is None:
        end = datetime.now(timezone.utc).date()
    if start is None:
        start = end - timedelta(days=30)
    return start, end


@router.get("/cfdi", response_model=CfdiReport)
def cfdi_report(
    *,
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: User = Depends(get_current_active_user),
) -> CfdiReport:
    """Realized sales in a CFDI 4.0-ready shape (export-only).

    Defaults to the last 30 days when no date range is given. Every order
    is issued to the RFC genérico ("PÚBLICO EN GENERAL") — the standard
    treatment for consumer marketplace sales. `issuer.is_configured` is
    false until the emisor RFC/name/régimen are set under Settings → CFDI.
    """
    start, end = _cfdi_date_range(start_date, end_date)
    return cfdi_service.build_cfdi_report(db, start_date=start, end_date=end, limit=limit)


def _cfdi_table(report: CfdiReport) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    issuer_rfc = report.issuer.rfc or "—"
    rows = [
        {
            "order_id": r.order_id,
            "external_order_id": r.external_order_id or "",
            "issued_at": r.issued_at,
            "source": r.source or "",
            "currency": r.currency,
            "issuer_rfc": issuer_rfc,
            "receiver_rfc": r.receiver_rfc,
            "receiver_name": r.receiver_name,
            "cfdi_use": r.cfdi_use,
            "subtotal": r.subtotal,
            "iva_amount": r.iva_amount,
            "total": r.total,
        }
        for r in report.rows
    ]
    return ReportTable(
        title="Fulcrum — CFDI Export (público en general)",
        subtitle=(
            f"Generated {date_stamp} · {report.order_count} orders · "
            f"subtotal {report.subtotal:.2f} · IVA {report.iva_amount:.2f} · "
            f"total {report.total:.2f}"
        ),
        filename_stem="fulcrum-cfdi",
        empty_message="No realized sales in the selected range.",
        columns=[
            ReportColumn("order_id",          "Order ID"),
            ReportColumn("external_order_id", "External #"),
            ReportColumn("issued_at",         "Issued",        formatter=fmt_date),
            ReportColumn("source",            "Channel"),
            ReportColumn("currency",          "Currency"),
            ReportColumn("issuer_rfc",        "Issuer RFC"),
            ReportColumn("receiver_rfc",      "Receiver RFC"),
            ReportColumn("receiver_name",     "Receiver"),
            ReportColumn("cfdi_use",          "CFDI use"),
            ReportColumn("subtotal",          "Subtotal",  align="right", formatter=fmt_float(2)),
            ReportColumn("iva_amount",        "IVA",       align="right", formatter=fmt_float(2)),
            ReportColumn("total",             "Total",     align="right", formatter=fmt_float(2)),
        ],
        rows=rows,
    )


@router.get("/cfdi/export")
def export_cfdi_csv(
    *,
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the CFDI-ready export as a CSV download (one row per order)."""
    start, end = _cfdi_date_range(start_date, end_date)
    report = cfdi_service.build_cfdi_report(db, start_date=start, end_date=end, limit=limit)
    return stream_csv(_cfdi_table(report))


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
    reason_code: Optional[str],
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
    if reason_code is not None:
        # Magic string `"none"` filters to NULL rows (legacy
        # uncategorized adjustments), matching the audit-page
        # dropdown's "Uncategorized" option. Any other value is
        # validated upstream as a known enum.
        if reason_code == "none":
            query = query.filter(InventoryAdjustment.reason_code.is_(None))
        else:
            query = query.filter(InventoryAdjustment.reason_code == reason_code)

    rows: list[dict] = []
    for adj in query.limit(limit).all():
        product = adj.product
        rows.append({
            "timestamp":    adj.timestamp or adj.created_at,
            "product_id":   adj.product_id,
            "product_sku":  product.sku if product else "",
            "product_name": product.name if product else "",
            "adjustment":   adj.adjustment,
            "reason_code":  adj.reason_code or "",
            "reason":       adj.reason or "",
            "created_by":   adj.created_by or "",
        })
    return rows


def _validate_reason_code_query(value: Optional[str]) -> Optional[str]:
    """Accept either a known enum value or the special string 'none'
    (for filtering to NULL legacy rows). Anything else is a 400."""
    if value is None:
        return None
    from src.models.inventory import InventoryAdjustmentReasonCode

    if value == "none":
        return value
    valid = {code.value for code in InventoryAdjustmentReasonCode}
    if value not in valid:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.inventoryAdjustment.unknownReasonCode",
            params={"value": value},
            detail=f"Unknown reason_code '{value}'",
        )
    return value


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
            ReportColumn("reason_code",  "Reason code"),
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
    reason_code: Optional[str] = None
    reason: Optional[str] = None
    created_by: Optional[str] = None
    # Reversal linkage (stock-movement audit). `reverses_adjustment_id`
    # is set when THIS row is a correction undoing an earlier one;
    # `reversed_by_id` is set when this row HAS BEEN reversed by a later
    # correction. `reversible` tells the UI whether to show a Reverse
    # action (operator-reversible reason code, not already reversed, not
    # itself a reversal).
    reverses_adjustment_id: Optional[int] = None
    reversed_by_id: Optional[int] = None
    reversible: bool = False


class ReverseAdjustmentRequest(BaseModel):
    """Optional free-text note appended to the auto-generated reversal
    reason ("Reversal of adjustment #N — <note>")."""
    note: Optional[str] = None


class InventoryAdjustmentList(BaseModel):
    rows: List[InventoryAdjustmentRow]
    total: int
    """Total matching rows ignoring pagination. The frontend uses this to
    render a paginator without a second round-trip."""


@router.get("/inventory-adjustments/reason-codes", response_model=List[str])
def list_inventory_adjustment_reason_codes(
    current_user: User = Depends(get_current_active_user),
) -> List[str]:
    """Return the canonical reason-code list so the audit-page
    dropdown can render it without hard-coding the enum on both
    sides. Order is enum declaration order — that's the order the
    operator sees in the dropdown.
    """
    from src.models.inventory import InventoryAdjustmentReasonCode

    return [code.value for code in InventoryAdjustmentReasonCode]


@router.get("/inventory-adjustments", response_model=InventoryAdjustmentList)
def list_inventory_adjustments(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    reason_code: Optional[str] = Query(
        None,
        description=(
            "Filter by reason code (shrinkage / recount / damage / return / "
            "theft / correction / sale / cancellation / transfer / purchase / "
            "manual / other). Pass 'none' to filter for legacy uncategorized "
            "rows."
        ),
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
):
    """Paginated audit log of every inventory quantity change. Newest first.
    Same filter shape as the CSV/PDF export endpoints so a buyer can find
    the rows on screen, then click Export to get the full filtered set."""
    from sqlalchemy.orm import joinedload as _joinedload

    reason_code = _validate_reason_code_query(reason_code)

    base = db.query(InventoryAdjustment)
    if product_id is not None:
        base = base.filter(InventoryAdjustment.product_id == product_id)
    if after is not None:
        base = base.filter(InventoryAdjustment.timestamp >= after)
    if before is not None:
        base = base.filter(InventoryAdjustment.timestamp <= before)
    if reason_code is not None:
        if reason_code == "none":
            base = base.filter(InventoryAdjustment.reason_code.is_(None))
        else:
            base = base.filter(InventoryAdjustment.reason_code == reason_code)

    total = base.count()

    from src.models.inventory import OPERATOR_REVERSIBLE_REASON_CODES

    page_q = (
        base.options(
            _joinedload(InventoryAdjustment.product),
            # Eager-load the backref so "has this been reversed?" doesn't
            # fire a query per row.
            _joinedload(InventoryAdjustment.reversed_by),
        )
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
        reversed_by = adj.reversed_by
        reversed_by_id = reversed_by.id if reversed_by else None
        reversible = (
            (adj.reason_code or "") in OPERATOR_REVERSIBLE_REASON_CODES
            and reversed_by_id is None
            and adj.reverses_adjustment_id is None
        )
        rows.append(
            InventoryAdjustmentRow(
                id=adj.id,
                timestamp=adj.timestamp or adj.created_at,
                product_id=adj.product_id,
                product_sku=product.sku if product else None,
                product_name=product.name if product else None,
                adjustment=adj.adjustment,
                reason_code=adj.reason_code,
                reason=adj.reason,
                created_by=adj.created_by,
                reverses_adjustment_id=adj.reverses_adjustment_id,
                reversed_by_id=reversed_by_id,
                reversible=reversible,
            )
        )
    return InventoryAdjustmentList(rows=rows, total=total)


@router.post(
    "/inventory-adjustments/{adjustment_id}/reverse",
    response_model=InventoryAdjustmentRow,
    status_code=201,
)
def reverse_inventory_adjustment(
    *,
    db: Session = Depends(get_db),
    adjustment_id: int,
    payload: ReverseAdjustmentRequest = ReverseAdjustmentRequest(),
    current_user: User = Depends(get_current_active_user),
):
    """Reverse an operator-entered inventory adjustment by booking an
    equal-and-opposite `correction` row linked back to the original.

    Only operator-reversible reason codes (shrinkage / recount / damage /
    theft / manual / other) can be reversed here — system rows (sale,
    cancellation, return, purchase, transfer, marketplace_sync) are owned
    by their order / PO / transfer workflow. Reversing is idempotent: a
    second attempt on the same row returns 409.
    """
    from src.services.inventory_service import AdjustmentReversalError

    actor = current_user.email or f"user_{current_user.id}"
    try:
        reversal = inventory_service.reverse_adjustment(
            db, adjustment_id, actor=actor, note=payload.note,
        )
    except AdjustmentReversalError as exc:
        status = 404 if exc.code == "not_found" else 409
        raise LocalizedHTTPException(
            status_code=status,
            code=f"apiErrors.inventoryAdjustment.{exc.code}",
            params={"id": adjustment_id},
            detail=str(exc),
        )
    db.commit()
    db.refresh(reversal)

    product = reversal.product
    return InventoryAdjustmentRow(
        id=reversal.id,
        timestamp=reversal.timestamp or reversal.created_at,
        product_id=reversal.product_id,
        product_sku=product.sku if product else None,
        product_name=product.name if product else None,
        adjustment=reversal.adjustment,
        reason_code=reversal.reason_code,
        reason=reversal.reason,
        created_by=reversal.created_by,
        reverses_adjustment_id=reversal.reverses_adjustment_id,
        reversed_by_id=None,
        reversible=False,
    )


@router.get("/inventory-adjustments/export")
def export_inventory_adjustments_csv(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    reason_code: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the inventory-adjustment audit log as a CSV. Sorted newest
    first. Default limit is 5000 (cap 20000) for "give me the whole
    quarter" audit requests."""
    reason_code = _validate_reason_code_query(reason_code)
    rows = _build_inventory_adjustment_rows(
        db, product_id=product_id, after=after, before=before,
        reason_code=reason_code, limit=limit,
    )
    return stream_csv(_inventory_adjustment_table(rows))


@router.get("/inventory-adjustments/export-pdf")
def export_inventory_adjustments_pdf(
    *,
    db: Session = Depends(get_db),
    product_id: Optional[int] = Query(None),
    after: Optional[datetime] = Query(None),
    before: Optional[datetime] = Query(None),
    reason_code: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=20000),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the inventory-adjustment audit log as a printable PDF."""
    reason_code = _validate_reason_code_query(reason_code)
    rows = _build_inventory_adjustment_rows(
        db, product_id=product_id, after=after, before=before,
        reason_code=reason_code, limit=limit,
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
    from src.services.order_cost_engine import aggregate_rollup

    parsed_source: Optional[str] = None
    if source:
        if not marketplace_catalog.is_valid_order_source(source):
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.report.unknownSource",
                params={"source": source},
                detail=f"Unknown source '{source}'",
            )
        parsed_source = source.strip().upper()

    rollup = aggregate_rollup(db, window_days=window_days, source=parsed_source)
    return CostRollupResponse(
        window_days=window_days,
        source=parsed_source if parsed_source else None,
        **rollup,
    )


# ---- Profit summary ("¿Gané o perdí?") ------------------------------------
#
# The owner's real bottom-line question: "did I make or lose money this
# period?" — order-contribution profit MINUS operating expenses, in one
# plain MXN number. This is the ONLY surface that performs the subtraction;
# every other consumer (a future export / email digest) should call this so
# the accounting semantics stay in one place.
#
# Period contract: ONE `period` enum. The endpoint resolves it ONCE into a
# [start, end] span, derives a matching rolling `window_days` for the cost
# rollup, and sums operating expenses over the SAME span — eliminating the
# window-vs-calendar mismatch that composing the two endpoints client-side
# would risk.


# Categories whose spend is (or will be) already represented in the order
# cost breakdown. Built so per-order ad attribution can switch this on later
# without an endpoint change. Defaults OFF (empty) so v1 behavior is
# predictable and auditable: we subtract the FULL expense total and surface a
# footnote instead. See the double-count note below.
_DOUBLE_COUNTED_CATEGORIES: set[str] = set()

# Verdict boundary: |bottom_line| at or under this (MXN) reads as "even"
# rather than a misleading centavo-level win/loss.
_EVEN_EPSILON = 0.005

_PROFIT_PERIODS = {"this_month", "last_7d", "last_30d"}


def _resolve_profit_window(period: str) -> _DateWindow:
    """Map the profit `period` enum to a `_DateWindow` ending at "now".

    All three periods end at the current instant, so the cost rollup's
    rolling `[now - window_days, now]` window and the expense sum over
    `[start.date(), end.date()]` cover the same span (asserted in tests).
    """
    now = datetime.now(timezone.utc)
    if period == "this_month":
        start_dt = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        label = "este mes"
    elif period == "last_7d":
        start_dt = now - timedelta(days=7)
        label = "7 días"
    elif period == "last_30d":
        start_dt = now - timedelta(days=30)
        label = "30 días"
    else:  # pragma: no cover - guarded by the Query enum
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.reports.invalidPeriod",
            params={"period": period},
            detail=f"Unknown period '{period}'",
        )
    return _DateWindow(start_dt=start_dt, end_dt=now, label=label)


class ProfitSummaryResponse(BaseModel):
    """The business bottom line for a period — contribution profit minus
    operating expenses — in one flat DTO the UI renders directly."""
    period: str
    start: str  # ISO date (UTC) of the resolved window start
    end: str    # ISO date (UTC) of the resolved window end
    window_days: int

    revenue_amount_mxn: float
    # cogs + marketplace_fees + shipping + ad_spend + other, collapsed into
    # one "costs of your sales" line for the non-accountant ladder.
    sales_costs_amount: float
    # = revenue - sales_costs (the existing cost-rollup net_profit_amount).
    contribution_profit_amount: float
    operating_expenses_amount: float
    # = contribution_profit - operating_expenses. The big honest number.
    bottom_line_amount: float
    net_margin_percent: Optional[float] = None

    orders: int
    has_realized_orders: bool
    # 'won' | 'lost' | 'even' — null when there are no realized orders, so
    # the UI shows the empty state instead of a fake "$0 / quedaste a mano".
    verdict: Optional[str] = None
    # True while the v1 rule subtracts the full expense total: ad/shipping
    # logged BOTH as an expense and inside per-order cost could double-count.
    double_count_warning: bool
    # The category-exclusion plumbing the rule asks for, surfaced for
    # auditability. Empty in v1.
    excluded_categories: List[str]


@router.get("/profit-summary", response_model=ProfitSummaryResponse)
def profit_summary_report(
    *,
    db: Session = Depends(get_db),
    period: str = Query(
        "this_month",
        description="Period enum: this_month | last_7d | last_30d.",
    ),
    current_user: User = Depends(get_current_active_user),
) -> ProfitSummaryResponse:
    """"¿Gané o perdí?" — the business bottom line for the period.

    Fans out to two existing surfaces over ONE resolved window:
      - `aggregate_rollup` (order cost breakdown) → contribution profit,
        i.e. revenue − cogs − marketplace_fees − shipping − ad_spend − other.
      - the expense-summary query path → operating expenses over the same
        calendar span.

    bottom_line = contribution_profit − operating_expenses.

    Double-counting rule (v1): order-level `ad_spend` defaults to 0 today
    and real ad/shipping spend is logged as an *expense*, so the practical
    overlap is near-zero. We therefore subtract the FULL expense total and
    set `double_count_warning=True` (UI shows a footnote). The
    `_DOUBLE_COUNTED_CATEGORIES` exclusion set is wired but defaults OFF so
    behavior stays predictable; flip it on when per-order ad attribution
    ships. `excluded_categories` echoes the active set for auditability.

    Empty state: with zero realized orders in the period we still 200 with
    zeros, but `has_realized_orders=False` and `verdict=None` so the UI
    renders an empty state rather than a misleading "$0 — quedaste a mano".
    """
    from src.services.order_cost_engine import aggregate_rollup
    from src.api.v1.endpoints.expenses import expense_total_over_window

    if period not in _PROFIT_PERIODS:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.reports.invalidPeriod",
            params={"period": period},
            detail=f"Unknown period '{period}'",
        )

    window = _resolve_profit_window(period)
    # Rolling window_days for the cost rollup. Ceil so a partial final day
    # is still covered; floored at 1 so an early-in-the-month "this_month"
    # never asks for a zero-day window.
    span_seconds = (window.end_dt - window.start_dt).total_seconds()
    window_days = max(1, math.ceil(span_seconds / 86400.0))

    rollup = aggregate_rollup(db, window_days=window_days)

    sales_costs = round(
        float(rollup["cogs_amount"])
        + float(rollup["marketplace_fees_amount"])
        + float(rollup["shipping_cost_amount"])
        + float(rollup["ad_spend_amount"])
        + float(rollup["other_cost_amount"]),
        4,
    )
    contribution = float(rollup["net_profit_amount"])

    operating_expenses = round(
        expense_total_over_window(
            db,
            start_date=window.start_dt.date(),
            end_date=window.end_dt.date(),
            exclude_categories=_DOUBLE_COUNTED_CATEGORIES or None,
        ),
        4,
    )

    bottom_line = round(contribution - operating_expenses, 4)
    orders = int(rollup["orders"])
    has_realized_orders = orders > 0

    verdict: Optional[str] = None
    if has_realized_orders:
        if bottom_line > _EVEN_EPSILON:
            verdict = "won"
        elif bottom_line < -_EVEN_EPSILON:
            verdict = "lost"
        else:
            verdict = "even"

    return ProfitSummaryResponse(
        period=period,
        start=window.start_dt.date().isoformat(),
        end=window.end_dt.date().isoformat(),
        window_days=window_days,
        revenue_amount_mxn=float(rollup["revenue_amount_mxn"]),
        sales_costs_amount=sales_costs,
        contribution_profit_amount=round(contribution, 4),
        operating_expenses_amount=operating_expenses,
        bottom_line_amount=bottom_line,
        net_margin_percent=rollup.get("net_margin_percent"),
        orders=orders,
        has_realized_orders=has_realized_orders,
        verdict=verdict,
        double_count_warning=not _DOUBLE_COUNTED_CATEGORIES,
        excluded_categories=sorted(_DOUBLE_COUNTED_CATEGORIES),
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
    # Catalog-governed source list (strings) — a marketplace added to
    # the catalog automatically gets a channel row here. `source` is a
    # plain string; it compares equal to the str-enum constants.
    for source in marketplace_catalog.order_sources():
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
            source=source,
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


# ---- Refunds list (drill-down for the widget) ------------------------------
#
# Per-event detail behind the refunds-summary rollup. The dashboard
# widget shows aggregate count + MXN per channel; clicking through
# lands here for "which orders, when, how much". One row per refund
# event — a single order that bounced cancelled→reopened→cancelled
# produces two rows so the operator can see the bounce.
#
# Sources, in order they appear on the list:
#   1. Status transitions out of the realized set (full-order refunds
#      / cancellations) — joins through `sales_order_status_events`.
#   2. Amazon partial-refund events from `amazon_order_refunds`.
#
# Pagination is offset-based to match the existing reports surface;
# bounded at 1000 rows per page to keep responses sane.


class RefundsListRow(BaseModel):
    """One refund event. `refund_kind` is `'order_cancelled'` for a
    full-order transition or `'amazon_partial'` for a partial-refund
    event."""
    refund_kind: str  # 'order_cancelled' | 'amazon_partial'
    order_id: int
    source: str
    external_order_id: Optional[str] = None
    # For order_cancelled rows: the transition timestamp.
    # For amazon_partial rows: the SP-API PostedDate.
    refunded_at: datetime
    # For order_cancelled rows: revenue from the OrderCostBreakdown
    # (full refund). For amazon_partial rows: the partial amount.
    refunded_amount_mxn: float
    # Status the order moved INTO (for cancellations) or the order's
    # current status (for partial refunds). Lets the operator
    # distinguish a `CANCELLED` order from a `SHIPPED`-with-partial-
    # refund.
    order_status: Optional[str] = None


class RefundsListResponse(BaseModel):
    """Envelope mirrors `/payments/` paging conventions: `items`
    array + `total` for the `{N–M of Total}` UI."""
    window_label: str
    items: List[RefundsListRow]
    total: int


@router.get("/refunds-list", response_model=RefundsListResponse)
def refunds_list_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None, description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    source: Optional[str] = Query(
        None, description="Optional channel filter (amazon / mercadolibre / fulcrum).",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> RefundsListResponse:
    """Per-event refund list. Used by the `/reports/refunds` page
    behind the dashboard widget's drill-down link.

    Returns rows for both full-order refunds (status transitions out
    of the realized set) and Amazon partial-refund events, sorted by
    refunded_at desc so the most-recent activity lands first.

    `source` filter applies to both kinds — for partial refunds the
    filter is implicit (`amazon_order_refunds` rows are by definition
    Amazon).
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

    parsed_source: Optional[str] = None
    if source:
        if not marketplace_catalog.is_valid_order_source(source):
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.report.unknownSource",
                params={"source": source},
                detail=f"Unknown source '{source}'",
            )
        parsed_source = source.strip().upper()

    # --- 1. Full-order refunds: dedup per (order_id, latest exit
    # transition in window). An order that bounced realized→cancel
    # several times still gets distinct rows here because each
    # transition row is a distinct event the operator might want to
    # see.
    txn_query = (
        db.query(
            SalesOrderStatusEvent.id.label("event_id"),
            SalesOrderStatusEvent.order_id,
            SalesOrderStatusEvent.changed_at,
            SalesOrderStatusEvent.to_status,
            SalesOrder.source,
            SalesOrder.external_order_id,
            SalesOrder.status,
            OrderCostBreakdown.revenue_amount_mxn,
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderStatusEvent.order_id)
        .outerjoin(OrderCostBreakdown, OrderCostBreakdown.order_id == SalesOrder.id)
        .filter(SalesOrderStatusEvent.changed_at >= window.start_dt)
        .filter(SalesOrderStatusEvent.changed_at <= window.end_dt)
        .filter(SalesOrderStatusEvent.from_status.in_(REALIZED_STATUSES))
        .filter(SalesOrderStatusEvent.to_status.notin_(REALIZED_STATUSES))
    )
    if parsed_source is not None:
        txn_query = txn_query.filter(SalesOrder.source == parsed_source)

    # --- 2. Amazon partial refunds in window.
    partial_query = (
        db.query(
            AmazonOrderRefund.id.label("refund_id"),
            AmazonOrderRefund.order_id,
            AmazonOrderRefund.posted_at,
            AmazonOrderRefund.refund_amount,
            SalesOrder.source,
            SalesOrder.external_order_id,
            SalesOrder.status,
        )
        .join(SalesOrder, SalesOrder.id == AmazonOrderRefund.order_id)
        .filter(AmazonOrderRefund.posted_at.isnot(None))
        .filter(AmazonOrderRefund.posted_at >= window.start_dt)
        .filter(AmazonOrderRefund.posted_at <= window.end_dt)
    )
    if parsed_source is not None and parsed_source != OrderSource.AMAZON:
        # Partial-refund rows are Amazon-only; a non-Amazon filter
        # drops them all.
        partial_query = partial_query.filter(False)

    txn_rows = txn_query.all()
    partial_rows = partial_query.all()

    rows: List[RefundsListRow] = []
    for r in txn_rows:
        rows.append(RefundsListRow(
            refund_kind="order_cancelled",
            order_id=r.order_id,
            source=r.source if r.source else "",
            external_order_id=r.external_order_id,
            refunded_at=r.changed_at,
            refunded_amount_mxn=round(float(r.revenue_amount_mxn or 0.0), 2),
            order_status=r.to_status,
        ))
    for r in partial_rows:
        rows.append(RefundsListRow(
            refund_kind="amazon_partial",
            order_id=r.order_id,
            source=r.source if r.source else "",
            external_order_id=r.external_order_id,
            refunded_at=r.posted_at,
            refunded_amount_mxn=round(float(r.refund_amount or 0.0), 2),
            order_status=r.status,
        ))

    # Most-recent first; ties broken by order_id desc so the order
    # the operator just clicked on stays near the top.
    rows.sort(key=lambda x: (x.refunded_at, x.order_id), reverse=True)

    total = len(rows)
    paged = rows[skip : skip + limit]
    return RefundsListResponse(
        window_label=window.label,
        items=paged,
        total=total,
    )


# ---- Refunds-summary export (CSV + PDF) ------------------------------------


def _refunds_summary_table(response: RefundsSummaryResponse) -> ReportTable:
    """Build the `ReportTable` for the refunds-summary export. Both
    CSV and PDF share this definition so the column order, headers,
    and number formatting stay aligned. The export shows one row
    per channel plus a `TOTAL` row appended at the bottom — that
    second pass matches what the operator reads on the dashboard
    widget (per-channel cards + a single hero totals row).
    """
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = [
        {
            "source": row.source,
            "refunds_count": row.refunds_count,
            "refunded_amount_mxn": row.refunded_amount_mxn,
            "realized_orders_count": row.realized_orders_count,
            "refund_rate_percent": row.refund_rate_percent,
        }
        for row in response.by_channel
    ]
    rows.append({
        "source": "TOTAL",
        "refunds_count": response.totals.refunds_count,
        "refunded_amount_mxn": response.totals.refunded_amount_mxn,
        "realized_orders_count": response.totals.realized_orders_count,
        "refund_rate_percent": response.totals.refund_rate_percent,
    })
    return ReportTable(
        title="Fulcrum — Refunds & Cancellations Summary",
        subtitle=(
            f"Generated {date_stamp} · {response.window_label} · "
            f"{response.totals.refunds_count} refund(s) · "
            f"${response.totals.refunded_amount_mxn:,.2f} refunded"
        ),
        filename_stem="fulcrum-refunds-summary",
        empty_message="No channels in the rollup.",
        columns=[
            ReportColumn("source",                "Channel"),
            ReportColumn("refunds_count",         "Refunds",          align="right", formatter=fmt_int),
            ReportColumn("refunded_amount_mxn",   "Refunded (MXN)",   align="right", formatter=fmt_currency),
            ReportColumn("realized_orders_count", "Realized orders",  align="right", formatter=fmt_int),
            ReportColumn("refund_rate_percent",   "Rate %",           align="right", formatter=fmt_percent),
        ],
        rows=rows,
    )


@router.get("/refunds-summary/export")
def export_refunds_summary_csv(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None, description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-channel refund rollup as a CSV. Same data as
    `/refunds-summary` plus a `TOTAL` row at the bottom — handy for
    handing to accounting at month-end."""
    summary = refunds_summary_report(
        db=db, window_days=window_days,
        start_date=start_date, end_date=end_date,
        current_user=current_user,
    )
    return stream_csv(_refunds_summary_table(summary))


@router.get("/refunds-summary/export-pdf")
def export_refunds_summary_pdf(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None, description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-channel refund rollup as a printable PDF."""
    summary = refunds_summary_report(
        db=db, window_days=window_days,
        start_date=start_date, end_date=end_date,
        current_user=current_user,
    )
    return stream_pdf(_refunds_summary_table(summary))


# ---- Reason-code summary (shrinkage, damage, theft, return, ...) -----------
#
# Per-reason-code rollup of inventory adjustments. Answers the literal
# operator question: "how much did I lose to shrinkage last month?".
#
# Uses the `inventory_adjustments.reason_code` column shipped alongside
# the audit-filter slice. Two metrics per code:
#   - `adjustments_count` — number of audit rows in the window.
#   - `total_units_delta` — signed sum of `adjustment` (negative for
#     write-offs like shrinkage; positive for purchases / returns).
#   - `total_capital_at_cost` — sum of |adjustment| × current
#     `Product.cost_price`. Lets the operator translate "5 units of
#     SKU X disappeared" into pesos. Uses current cost because we
#     don't snapshot cost on the adjustment row (the audit tracks
#     quantity moves, not value moves).
#
# Window + date-range params via the shared `_resolve_date_window`
# helper. Legacy (NULL) reason_code rows roll up under the literal
# `"none"` source.


class ReasonCodeSummaryRow(BaseModel):
    """One row per `reason_code` (and optionally `location`) that had
    at least one adjustment in the window. NULL reason_code rows are
    surfaced under `reason_code='none'` so the operator can see how
    much legacy uncategorized data is still around without writing a
    custom query.

    `location` is None when the response wasn't grouped by location.
    When `group_by_location=True`, rows are emitted per
    (reason_code, location) tuple and the unknown-location sentinel
    is `'(unknown)'`.
    """
    reason_code: str
    adjustments_count: int
    total_units_delta: int
    total_capital_at_cost: float
    location: Optional[str] = None


class ReasonCodeSummaryResponse(BaseModel):
    """Subtitle-style label mirrors the velocity/margin/stockout
    endpoints so dashboard widgets can reuse the same wording
    ('window 30d' vs. '2026-01-01 → 2026-03-31')."""
    window_label: str
    rows: List[ReasonCodeSummaryRow]


def _build_reason_code_summary(
    db: Session,
    *,
    window,
    location: Optional[str] = None,
    group_by_location: bool = False,
) -> ReasonCodeSummaryResponse:
    """Compute the per-reason-code rollup over the resolved window.

    Joins through `Product` to pull `cost_price` for the capital
    calculation. Adjustments whose product was deleted (FK SET NULL
    on `product_id`, though the schema doesn't currently set null —
    the relationship is plain FK) carry `cost_price=0` for that row
    via COALESCE — surfaced as zero capital rather than crashing.

    Optional `location` filter narrows to a single warehouse/shelf.
    Optional `group_by_location` emits one row per
    (reason_code, location) so the dashboard can split a single
    reason across multiple sites — typical use: "where is the
    shrinkage concentrated?" NULL `location` rows (legacy data
    before the column existed) surface as `'(unknown)'`.
    """
    from src.models.inventory import InventoryAdjustment
    from src.models.product import Product

    reason_label = func.coalesce(InventoryAdjustment.reason_code, "none").label("reason_code")
    location_label = func.coalesce(InventoryAdjustment.location, "(unknown)").label("location")
    capital_expr = func.coalesce(
        func.sum(
            func.abs(InventoryAdjustment.adjustment)
            * func.coalesce(Product.cost_price, 0.0)
        ),
        0.0,
    )

    group_cols = [reason_label]
    select_cols = [
        reason_label,
        func.count(InventoryAdjustment.id).label("adjustments_count"),
        func.coalesce(func.sum(InventoryAdjustment.adjustment), 0).label("total_units_delta"),
        capital_expr.label("total_capital_at_cost"),
    ]
    if group_by_location:
        group_cols.append(location_label)
        select_cols.append(location_label)

    q = (
        db.query(*select_cols)
        .outerjoin(Product, Product.id == InventoryAdjustment.product_id)
        .filter(InventoryAdjustment.timestamp >= window.start_dt)
        .filter(InventoryAdjustment.timestamp <= window.end_dt)
    )
    if location is not None:
        q = q.filter(InventoryAdjustment.location == location)
    q = (
        q.group_by(*group_cols)
        # Sort by capital-at-risk desc so the operator's eye lands on
        # the biggest dollar impact first, regardless of category.
        .order_by(capital_expr.desc())
    )

    rows_raw = q.all()

    return ReasonCodeSummaryResponse(
        window_label=window.label,
        rows=[
            ReasonCodeSummaryRow(
                reason_code=r.reason_code,
                adjustments_count=int(r.adjustments_count or 0),
                total_units_delta=int(r.total_units_delta or 0),
                total_capital_at_cost=round(float(r.total_capital_at_cost or 0.0), 2),
                location=(r.location if group_by_location else None),
            )
            for r in rows_raw
        ],
    )


@router.get("/reason-code-summary", response_model=ReasonCodeSummaryResponse)
def reason_code_summary_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None, description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    location: Optional[str] = Query(
        None, description="Optional warehouse / shelf filter (matches inventory_adjustments.location exactly).",
    ),
    group_by_location: bool = Query(
        False, description="When true, emit one row per (reason_code, location).",
    ),
    current_user: User = Depends(get_current_active_user),
) -> ReasonCodeSummaryResponse:
    """Per-reason-code rollup of inventory adjustments. Answers
    "how much did I lose to shrinkage last month?" + the same
    question for every other code (damage, theft, correction, etc.).

    Counts every adjustment regardless of sign — the operator gets
    the unsigned units sum to read "how much moved through this
    bucket?" and `total_units_delta` to read "net direction".

    `location` filter narrows to one warehouse; `group_by_location`
    splits the rollup into per-(reason, location) rows so the
    dashboard can show "shrinkage is concentrated at aisle-3".
    Legacy rows pre-dating the location column surface under
    `'(unknown)'`.
    """
    window = _resolve_date_window(window_days, start_date, end_date)
    return _build_reason_code_summary(
        db, window=window,
        location=location, group_by_location=group_by_location,
    )


def _reason_code_summary_table(
    response: ReasonCodeSummaryResponse, *, include_location: bool = False,
) -> ReportTable:
    """Shared ReportTable for the CSV + PDF exports. Same row order
    as the JSON endpoint (capital-at-risk desc). When the response
    was grouped by location, an extra `location` column shows up
    between reason_code and the numeric columns."""
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_capital = sum(r.total_capital_at_cost for r in response.rows)
    total_count = sum(r.adjustments_count for r in response.rows)
    columns = [
        ReportColumn("reason_code", "Reason"),
    ]
    if include_location:
        columns.append(ReportColumn("location", "Location"))
    columns.extend([
        ReportColumn("adjustments_count",     "Adjustments",       align="right", formatter=fmt_int),
        ReportColumn("total_units_delta",     "Net units (signed)", align="right", formatter=fmt_int),
        ReportColumn("total_capital_at_cost", "Capital (MXN)",     align="right", formatter=fmt_currency),
    ])
    return ReportTable(
        title="Fulcrum — Inventory Adjustments by Reason Code",
        subtitle=(
            f"Generated {date_stamp} · {response.window_label} · "
            f"{total_count:,} adjustment(s) · "
            f"${total_capital:,.2f} capital affected"
        ),
        filename_stem="fulcrum-reason-code-summary",
        empty_message="No inventory adjustments in the window.",
        columns=columns,
        rows=[r.model_dump() for r in response.rows],
    )


@router.get("/reason-code-summary/export")
def export_reason_code_summary_csv(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    location: Optional[str] = Query(None),
    group_by_location: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-reason-code rollup as a CSV — operator-facing answer to
    "how much did I lose / move through each bucket last month?".
    Honors the same location / group_by_location params as the JSON
    endpoint.
    """
    window = _resolve_date_window(window_days, start_date, end_date)
    summary = _build_reason_code_summary(
        db, window=window,
        location=location, group_by_location=group_by_location,
    )
    return stream_csv(_reason_code_summary_table(
        summary, include_location=group_by_location,
    ))


@router.get("/reason-code-summary/export-pdf")
def export_reason_code_summary_pdf(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    location: Optional[str] = Query(None),
    group_by_location: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Per-reason-code rollup as a printable PDF."""
    window = _resolve_date_window(window_days, start_date, end_date)
    summary = _build_reason_code_summary(
        db, window=window,
        location=location, group_by_location=group_by_location,
    )
    return stream_pdf(_reason_code_summary_table(
        summary, include_location=group_by_location,
    ))


# ---- Returns summary (dashboard widget) ------------------------------------
#
# Mirror of the refunds-summary surface, but for *physical* returns
# captured by the returns workflow (`sales_order_returns` rows). The
# refunds widget answers "how many money-out events happened?"; this
# widget answers "how much stock came back?". Both are operator-
# facing dashboard signals; together they cover the financial and
# physical sides of the return relationship.
#
# Per channel:
#   - `returns_count` — number of return events.
#   - `units_returned` — sum of `quantity` across events.
#   - `value_at_cost_mxn` — sum of quantity × current
#     `Product.cost_price`. Cost-basis (not retail) because the
#     dashboard signal is "how much inventory value came back",
#     which is the operator's exposure if they discount or write
#     off the returned units.


class ReturnsByChannelRow(BaseModel):
    source: str
    returns_count: int
    units_returned: int
    value_at_cost_mxn: float


class ReturnsSummaryResponse(BaseModel):
    window_label: str
    totals: ReturnsByChannelRow
    by_channel: List[ReturnsByChannelRow]


@router.get("/returns-summary", response_model=ReturnsSummaryResponse)
def returns_summary_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> ReturnsSummaryResponse:
    """Per-channel physical-return rollup over the window. Powers
    the dashboard's returns widget.

    Joins `sales_order_returns` through `sales_orders.source` for
    the channel attribution + `products.cost_price` for the value
    calculation. Returns rows for sources that recorded any return
    activity in the window; channels with zero activity are omitted
    so the widget doesn't render empty rows."""
    from src.models.order import SalesOrder, SalesOrderReturn
    from src.models.product import Product

    window = _resolve_date_window(window_days, start_date, end_date)

    rows_raw = (
        db.query(
            SalesOrder.source,
            func.count(SalesOrderReturn.id).label("returns_count"),
            func.coalesce(func.sum(SalesOrderReturn.quantity), 0).label("units_returned"),
            func.coalesce(
                func.sum(
                    SalesOrderReturn.quantity
                    * func.coalesce(Product.cost_price, 0.0)
                ),
                0.0,
            ).label("value_at_cost_mxn"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderReturn.order_id)
        .outerjoin(Product, Product.id == SalesOrderReturn.product_id)
        .filter(SalesOrderReturn.received_at >= window.start_dt)
        .filter(SalesOrderReturn.received_at <= window.end_dt)
        .group_by(SalesOrder.source)
        .all()
    )

    by_channel: List[ReturnsByChannelRow] = []
    total_count = 0
    total_units = 0
    total_value = 0.0
    for source, count_, units, value in rows_raw:
        # `source` is the SQLAlchemy enum on SalesOrder.source. If a
        # legacy order has a NULL source the row falls into an "UNKNOWN"
        # bucket so the operator can see the orphan instead of silently
        # losing it.
        source_label = source if source is not None else "UNKNOWN"
        by_channel.append(ReturnsByChannelRow(
            source=source_label,
            returns_count=int(count_ or 0),
            units_returned=int(units or 0),
            value_at_cost_mxn=round(float(value or 0.0), 2),
        ))
        total_count += int(count_ or 0)
        total_units += int(units or 0)
        total_value += float(value or 0.0)

    # Sort by value desc so the operator's eye lands on the biggest
    # capital-came-back channel first.
    by_channel.sort(key=lambda r: r.value_at_cost_mxn, reverse=True)

    totals = ReturnsByChannelRow(
        source="ALL",
        returns_count=total_count,
        units_returned=total_units,
        value_at_cost_mxn=round(total_value, 2),
    )

    return ReturnsSummaryResponse(
        window_label=window.label,
        totals=totals,
        by_channel=by_channel,
    )


# ---------------------------------------------------------------------------
# Returns drill-down list (used by /reports/returns frontend page)
# ---------------------------------------------------------------------------


class ReturnsListRow(BaseModel):
    """One row per `sales_order_returns` event. The frontend page
    renders these in a Material table; the dashboard widget hero
    links here when the operator wants to drill in.

    `value_at_cost` uses `Product.cost_price × quantity` so the
    operator can sort by where the cost-of-returns concentrates.
    """
    return_id: int
    received_at: datetime
    order_id: int
    external_order_id: Optional[str]
    source: Optional[str]
    product_id: Optional[int]
    product_sku: Optional[str]
    product_name: Optional[str]
    quantity: int
    reason: Optional[str]
    notes: Optional[str]
    recorded_by_email: Optional[str]
    value_at_cost: float


class ReturnsListResponse(BaseModel):
    """Envelope mirrors `/refunds-list`: `items` array + `total`."""
    window_label: str
    items: List[ReturnsListRow]
    total: int


@router.get("/returns-list", response_model=ReturnsListResponse)
def returns_list_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(
        None, description="Inclusive lower bound (UTC). Overrides window_days when set.",
    ),
    end_date: Optional[date] = Query(
        None, description="Inclusive upper bound (UTC). Overrides window_days when set.",
    ),
    source: Optional[str] = Query(
        None, description="Optional channel filter (amazon / mercadolibre / fulcrum).",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> ReturnsListResponse:
    """Per-event returns drill-down. One row per
    `sales_order_returns` entry in the window, sorted by
    received_at desc.

    Page-friendly: returns `total` so the UI can render N–M of T.
    Joins to `sales_orders` for source + external_order_id, to
    `products` for sku/name/cost, and to `users` for the operator
    email."""
    from src.models.order import SalesOrder, SalesOrderReturn
    from src.models.product import Product

    window = _resolve_date_window(window_days, start_date, end_date)

    parsed_source: Optional[str] = None
    if source:
        if not marketplace_catalog.is_valid_order_source(source):
            raise LocalizedHTTPException(
                status_code=400,
                code="apiErrors.report.unknownSource",
                params={"source": source},
                detail=f"Unknown source '{source}'",
            )
        parsed_source = source.strip().upper()

    base = (
        db.query(
            SalesOrderReturn,
            SalesOrder.source.label("source"),
            SalesOrder.external_order_id.label("external_order_id"),
            Product.sku.label("product_sku"),
            Product.name.label("product_name"),
            Product.cost_price.label("cost_price"),
            User.email.label("recorder_email"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderReturn.order_id)
        .outerjoin(Product, Product.id == SalesOrderReturn.product_id)
        .outerjoin(User, User.id == SalesOrderReturn.recorded_by_user_id)
        .filter(SalesOrderReturn.received_at >= window.start_dt)
        .filter(SalesOrderReturn.received_at <= window.end_dt)
    )
    if parsed_source is not None:
        base = base.filter(SalesOrder.source == parsed_source)

    total = base.count()

    rows = (
        base.order_by(SalesOrderReturn.received_at.desc(), SalesOrderReturn.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items: List[ReturnsListRow] = []
    for r, src, ext_id, sku, name, cost, recorder in rows:
        cost_val = float(cost or 0)
        qty = int(r.quantity or 0)
        items.append(ReturnsListRow(
            return_id=r.id,
            received_at=r.received_at,
            order_id=r.order_id,
            external_order_id=ext_id,
            source=src if src is not None else None,
            product_id=r.product_id,
            product_sku=sku,
            product_name=name,
            quantity=qty,
            reason=r.reason,
            notes=r.notes,
            recorded_by_email=recorder,
            value_at_cost=round(cost_val * qty, 2),
        ))

    return ReturnsListResponse(
        window_label=window.label,
        items=items,
        total=total,
    )


# --------------------------------------------------------------------------- #
# Buyer Q&A (marketplace questions) + response-time SLA
# --------------------------------------------------------------------------- #

# Hours a buyer question may sit unanswered before it counts as an SLA
# breach. MercadoLibre weighs response time into seller reputation, so a
# conservative 24h horizon flags questions that risk hurting it.
QA_SLA_HOURS = 24


class QuestionRow(BaseModel):
    id: int
    external_question_id: str
    source: str
    item_id: Optional[str] = None
    # Human product/listing title resolved from the listing's product via
    # the raw ML `item_id`. NULL when the item_id has no matching listing.
    item_name: Optional[str] = None
    buyer_id: Optional[str] = None
    question_text: Optional[str] = None
    answer_text: Optional[str] = None
    status: Optional[str] = None
    asked_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    answered: bool
    # Hours the question has been open (response time if answered, current
    # age if still open). None when asked_at is missing.
    hours_open: Optional[float] = None
    sla_status: str  # 'answered' | 'pending' | 'breached'


class QuestionsListResponse(BaseModel):
    rows: List[QuestionRow]
    total: int
    sla_hours: int = QA_SLA_HOURS
    unanswered_count: int
    breached_count: int
    answered_count: int


@router.get("/questions", response_model=QuestionsListResponse)
def questions_list_report(
    *,
    db: Session = Depends(get_db),
    window_days: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(
        None, description="'unanswered' / 'answered', or an exact marketplace status.",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> QuestionsListResponse:
    """Buyer-question inbox + response-time SLA. One row per
    `marketplace_questions` entry asked in the window, newest first.
    `sla_status` is 'answered', 'pending' (open, within SLA), or
    'breached' (open longer than `sla_hours`)."""
    from sqlalchemy import func as _sqlfunc
    from src.models.marketplace import (
        Marketplace,
        MarketplaceListing,
        MarketplaceQuestion,
    )
    from src.models.product import Product

    window = _resolve_date_window(window_days, start_date, end_date)
    now = datetime.now(timezone.utc)
    breach_cutoff = now - timedelta(hours=QA_SLA_HOURS)

    # Resolve the raw ML `item_id` → a human product title. A single
    # (marketplace_id, external_listing_id) can in principle map to more
    # than one listing row, so collapse to one product name per key via a
    # grouped subquery — that keeps the LEFT JOIN strictly 1:1 with the
    # question rows (no duplication, no effect on total/pagination).
    item_name_sq = (
        db.query(
            MarketplaceListing.marketplace_id.label("marketplace_id"),
            MarketplaceListing.external_listing_id.label("external_listing_id"),
            _sqlfunc.min(Product.name).label("item_name"),
        )
        .join(Product, Product.id == MarketplaceListing.product_id)
        .filter(MarketplaceListing.external_listing_id.isnot(None))
        .filter(Product.name.isnot(None))
        .group_by(
            MarketplaceListing.marketplace_id,
            MarketplaceListing.external_listing_id,
        )
        .subquery()
    )

    base = (
        db.query(
            MarketplaceQuestion,
            Marketplace.name.label("source"),
            item_name_sq.c.item_name.label("item_name"),
        )
        .outerjoin(Marketplace, Marketplace.id == MarketplaceQuestion.marketplace_id)
        .outerjoin(
            item_name_sq,
            (item_name_sq.c.external_listing_id == MarketplaceQuestion.item_id)
            & (item_name_sq.c.marketplace_id == MarketplaceQuestion.marketplace_id),
        )
        .filter(MarketplaceQuestion.asked_at >= window.start_dt)
        .filter(MarketplaceQuestion.asked_at <= window.end_dt)
    )
    status_norm = (status or "").strip().lower()
    if status_norm == "unanswered":
        base = base.filter(MarketplaceQuestion.answered_at.is_(None))
    elif status_norm == "answered":
        base = base.filter(MarketplaceQuestion.answered_at.isnot(None))
    elif status:
        base = base.filter(MarketplaceQuestion.status == status)

    total = base.count()
    answered_count = base.filter(MarketplaceQuestion.answered_at.isnot(None)).count()
    breached_count = (
        base.filter(MarketplaceQuestion.answered_at.is_(None))
        .filter(MarketplaceQuestion.asked_at < breach_cutoff)
        .count()
    )

    page = (
        base.order_by(
            MarketplaceQuestion.asked_at.desc().nullslast(),
            MarketplaceQuestion.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    def _hours(a: datetime, b: datetime) -> float:
        return round((b - a).total_seconds() / 3600.0, 1)

    rows: List[QuestionRow] = []
    for q, source_name, item_name in page:
        answered = q.answered_at is not None
        hours_open: Optional[float] = None
        if q.asked_at is not None:
            hours_open = _hours(q.asked_at, q.answered_at if answered else now)
        if answered:
            sla = "answered"
        elif q.asked_at is not None and q.asked_at < breach_cutoff:
            sla = "breached"
        else:
            sla = "pending"
        rows.append(QuestionRow(
            id=q.id,
            external_question_id=q.external_question_id,
            source=source_name or "MERCADOLIBRE",
            item_id=q.item_id,
            item_name=item_name,
            buyer_id=q.buyer_id,
            question_text=q.question_text,
            answer_text=q.answer_text,
            status=q.status,
            asked_at=q.asked_at,
            answered_at=q.answered_at,
            answered=answered,
            hours_open=hours_open,
            sla_status=sla,
        ))

    return QuestionsListResponse(
        rows=rows,
        total=total,
        unanswered_count=total - answered_count,
        breached_count=breached_count,
        answered_count=answered_count,
    )


class AnswerQuestionRequest(BaseModel):
    text: str


def _question_row(
    q, source_name: Optional[str], item_name: Optional[str] = None,
) -> "QuestionRow":
    """Build a `QuestionRow` from a `MarketplaceQuestion`, recomputing the
    response-time SLA fields exactly like the list endpoint does.

    `item_name` is the resolved human product title (NULL when the
    item_id has no matching listing); callers resolve it via
    `_resolve_question_item_name`."""
    now = datetime.now(timezone.utc)
    breach_cutoff = now - timedelta(hours=QA_SLA_HOURS)
    answered = q.answered_at is not None
    hours_open: Optional[float] = None
    if q.asked_at is not None:
        end = q.answered_at if answered else now
        hours_open = round((end - q.asked_at).total_seconds() / 3600.0, 1)
    if answered:
        sla = "answered"
    elif q.asked_at is not None and q.asked_at < breach_cutoff:
        sla = "breached"
    else:
        sla = "pending"
    return QuestionRow(
        id=q.id,
        external_question_id=q.external_question_id,
        source=source_name or "MERCADOLIBRE",
        item_id=q.item_id,
        item_name=item_name,
        buyer_id=q.buyer_id,
        question_text=q.question_text,
        answer_text=q.answer_text,
        status=q.status,
        asked_at=q.asked_at,
        answered_at=q.answered_at,
        answered=answered,
        hours_open=hours_open,
        sla_status=sla,
    )


def _resolve_question_item_name(db: Session, q) -> Optional[str]:
    """Resolve a single question's raw `item_id` → human product title via
    its marketplace listing's product, mirroring the list endpoint's join.
    Returns NULL when there's no item_id or no matching listing/product."""
    if not q.item_id:
        return None
    from src.models.marketplace import MarketplaceListing
    from src.models.product import Product

    return (
        db.query(Product.name)
        .join(MarketplaceListing, MarketplaceListing.product_id == Product.id)
        .filter(MarketplaceListing.external_listing_id == q.item_id)
        .filter(MarketplaceListing.marketplace_id == q.marketplace_id)
        .filter(Product.name.isnot(None))
        .order_by(Product.name.asc())
        .limit(1)
        .scalar()
    )


@router.post("/questions/{question_id}/answer", response_model=QuestionRow)
def answer_question_endpoint(
    *,
    db: Session = Depends(get_db),
    question_id: int,
    payload: AnswerQuestionRequest,
    current_user: User = Depends(get_current_active_user),
) -> "QuestionRow":
    """Post a seller reply to a buyer question (MercadoLibre) and return the
    updated row. An expired ML token surfaces a 409 with a machine-readable
    `code` so the UI can show an inline Reconnect affordance."""
    from src.models.marketplace import Marketplace
    from src.services import questions_service

    result = questions_service.answer_question(db, question_id, payload.text)
    err = result.get("error")
    if err == "empty":
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.question.emptyAnswer",
            detail="Answer text must not be empty.",
        )
    if err == "not_found":
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.question.notFound",
            params={"id": question_id},
            detail=f"Question {question_id} not found.",
        )
    if err == "already_answered":
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.question.alreadyAnswered",
            params={"id": question_id},
            detail=f"Question {question_id} is already answered.",
        )
    if err == "needs_reauthorization":
        raise LocalizedHTTPException(
            status_code=409,
            code="needs_reauthorization",
            detail="MercadoLibre authorization expired; reconnect to answer.",
        )
    if err in ("unsupported", "connector_unavailable"):
        raise LocalizedHTTPException(
            status_code=502,
            code="apiErrors.question.unsupported",
            detail="Answering is not supported for this marketplace.",
        )
    if err:
        raise LocalizedHTTPException(
            status_code=500,
            code="apiErrors.question.answerFailed",
            detail="Failed to post the answer to the marketplace.",
        )

    q = result["question"]
    source_name = (
        db.query(Marketplace.name)
        .filter(Marketplace.id == q.marketplace_id)
        .scalar()
    )
    item_name = _resolve_question_item_name(db, q)
    return _question_row(q, source_name, item_name)
