"""
Operational reports surface. Currently exposes the low-stock report used
by the dashboard widget; future stockout/velocity/margin reports should
live here too.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.api.dependencies import get_current_active_user
from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.database import get_db
from src.models.inventory import InventoryItem
from src.models.product import Product
from src.models.product_inventory_settings import ProductInventorySettings
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
