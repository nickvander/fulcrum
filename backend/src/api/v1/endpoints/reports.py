"""
Operational reports surface. Currently exposes the low-stock report used
by the dashboard widget; future stockout/velocity/margin reports should
live here too.
"""
import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.api.dependencies import get_current_active_user
from src.core.errors import LocalizedHTTPException
from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.database import get_db
from src.models.inventory import InventoryItem
from src.models.product import Product
from src.models.product_inventory_settings import ProductInventorySettings
from src.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from src.models.purchase_order_item import PurchaseOrderItem
from src.models.supplier_product import SupplierProduct
from src.models.user import User
from src.services.inventory_service import inventory_service


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
# CSV export
# ---------------------------------------------------------------------------

@router.get("/low-stock/export")
def export_low_stock_csv(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(500, ge=1, le=5000),
    velocity_window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    Stream the low-stock report as a CSV download.

    Columns mirror the rows in the JSON report — same data, just in a
    shape that Excel / Google Sheets opens directly. Useful when the
    buyer wants to triage / annotate the list outside the app, or to
    email it to a supplier rep.

    The default `limit` here is 500 (vs. 50 on the JSON endpoint)
    because the export use case is "give me everything"; the cap stays
    at 5000 so a degenerate inventory doesn't blow up the response.

    Filename includes the date so successive exports don't collide in
    the user's Downloads folder.
    """
    report = low_stock_report(
        db=db, limit=limit, velocity_window_days=velocity_window_days,
        current_user=current_user,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "product_id", "product_sku", "product_name",
        "severity", "on_hand", "threshold",
        "reorder_point", "reorder_quantity", "suggested_reorder_qty",
        "daily_velocity", "days_of_inventory",
    ])
    for row in report.rows:
        writer.writerow([
            row.product_id, row.product_sku or "", row.product_name,
            row.severity, row.on_hand, row.threshold,
            row.reorder_point if row.reorder_point is not None else "",
            row.reorder_quantity if row.reorder_quantity is not None else "",
            row.suggested_reorder_qty,
            row.daily_velocity, row.days_of_inventory,
        ])
    buf.seek(0)

    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"fulcrum-low-stock-{date_stamp}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/low-stock/export-pdf")
def export_low_stock_pdf(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(500, ge=1, le=5000),
    velocity_window_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Render the low-stock report as a printable PDF.

    Same data and limits as the CSV export. The PDF is laid out in landscape
    so the wide table fits without re-flowing, and rows are color-coded by
    severity (critical = red, low = orange, watch = light yellow) so the
    buyer can scan the page at a glance — closer to what an "accountant
    handoff" PDF needs to look like than the CSV.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    report = low_stock_report(
        db=db, limit=limit, velocity_window_days=velocity_window_days,
        current_user=current_user,
    )

    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        title="Fulcrum Low-Stock Report",
        leftMargin=0.4 * inch, rightMargin=0.4 * inch,
        topMargin=0.5 * inch, bottomMargin=0.4 * inch,
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>Fulcrum — Low-Stock Report</b>", styles["Title"]),
        Paragraph(
            f"Generated {date_stamp} · {report.total_critical} critical · "
            f"{report.total_low} low · {report.total_watch} watch",
            styles["Normal"],
        ),
        Spacer(1, 0.15 * inch),
    ]

    header = [
        "SKU", "Product", "Severity",
        "On hand", "Threshold", "Reorder pt", "Reorder qty",
        "Suggested", "Daily velocity", "Days left",
    ]
    data = [header]
    for row in report.rows:
        data.append([
            row.product_sku or "",
            row.product_name,
            row.severity,
            str(row.on_hand),
            str(row.threshold),
            "" if row.reorder_point is None else str(row.reorder_point),
            "" if row.reorder_quantity is None else str(row.reorder_quantity),
            str(row.suggested_reorder_qty),
            f"{row.daily_velocity:.2f}",
            f"{row.days_of_inventory:.1f}" if row.days_of_inventory is not None else "",
        ])

    # Color rows by severity so the page is scannable
    severity_bg = {
        "critical": colors.HexColor("#fde7e7"),
        "low": colors.HexColor("#fff4d6"),
        "watch": colors.HexColor("#f0f4ff"),
    }
    table = Table(data, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
    for idx, row in enumerate(report.rows, start=1):
        bg = severity_bg.get(row.severity)
        if bg:
            style.add("BACKGROUND", (0, idx), (-1, idx), bg)
    table.setStyle(style)
    elements.append(table)

    if not report.rows:
        elements.append(Paragraph("No products are at or below threshold.", styles["Italic"]))

    doc.build(elements)
    buf.seek(0)

    filename = f"fulcrum-low-stock-{date_stamp}.pdf"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
