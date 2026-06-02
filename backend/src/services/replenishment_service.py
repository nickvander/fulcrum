"""Lead-time-aware replenishment-to-Full planner (B4).

Adds the *when* the low-stock report lacks. For each SKU selling on
MercadoLibre it computes two dated actions across the two-stage Mexico
supply chain (supplier -> internal warehouse -> ML Full):

  * **Send to Full by** — when internal stock must ship to ML Full before
    Full cover drops below the Full-transfer lead time.
  * **Reorder from supplier by** — when the whole pipeline
    (internal + Full + in-transit) must be topped up from the supplier,
    accounting for `SupplierProduct.lead_time_days`.

Velocity is scoped to MercadoLibre realized sales — Full inventory is
consumed by ML sales, so an Amazon sale doesn't draw down Full stock.
This mirrors `alert_evaluation_service._evaluate_ml_full_stockout_risk`
so the alert and the planner agree on the numbers.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.models.stock_transfer import (
    LOCATION_INTERNAL,
    LOCATION_ML_FULL,
    StockTransfer,
    StockTransferItem,
    StockTransferStatus,
)
from src.models.supplier_product import SupplierProduct
from src.schemas.replenishment import ReplenishmentReport, ReplenishmentRow

# Realized-sales statuses — mirrors the margin/velocity reports and the
# stockout alert so every surface agrees on what counts as a sale.
_REALIZED_ORDER_STATUSES = ("COMPLETED", "SHIPPED")

# Transfer states whose units are still on their way to the destination,
# so stock already shipped to Full isn't read as missing.
_IN_TRANSIT_TRANSFER_STATUSES = (
    StockTransferStatus.SHIPPED.value,
    StockTransferStatus.PARTIALLY_RECEIVED.value,
)

# Default Full-transfer lead time (days from "ship from internal" to
# "received and sellable at ML Full"). Matches the 14-day horizon the
# stockout alert uses (`_ML_FULL_COVER_HORIZON_DAYS`).
DEFAULT_FULL_TRANSFER_LEAD_DAYS = 14

# Fallback supplier lead time when a product has no SupplierProduct row
# with `lead_time_days` set.
DEFAULT_SUPPLIER_LEAD_DAYS = 30


def _ml_velocity_by_product(db: Session, cutoff: datetime, window_days: int) -> Dict[int, float]:
    """ML-channel realized units/day per product over the window."""
    rows = (
        db.query(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .filter(SalesOrder.created_at >= cutoff)
        .filter(SalesOrder.status.in_(_REALIZED_ORDER_STATUSES))
        .filter(SalesOrder.source == OrderSource.MERCADOLIBRE.value)
        .group_by(SalesOrderItem.product_id)
        .all()
    )
    return {
        pid: (int(units or 0) / window_days if window_days else 0.0)
        for pid, units in rows
        if pid is not None
    }


def _on_hand_at(db: Session, location: str) -> Dict[int, int]:
    rows = (
        db.query(
            InventoryItem.product_id,
            func.coalesce(func.sum(InventoryItem.quantity), 0),
        )
        .filter(InventoryItem.location == location)
        .group_by(InventoryItem.product_id)
        .all()
    )
    return {pid: int(qty or 0) for pid, qty in rows if pid is not None}


def _in_transit_to_full(db: Session) -> Dict[int, int]:
    rows = (
        db.query(
            StockTransferItem.product_id,
            func.coalesce(
                func.sum(StockTransferItem.qty_shipped - StockTransferItem.qty_received), 0
            ),
        )
        .join(StockTransfer, StockTransfer.id == StockTransferItem.transfer_id)
        .filter(StockTransfer.dest_location == LOCATION_ML_FULL)
        .filter(StockTransfer.status.in_(_IN_TRANSIT_TRANSFER_STATUSES))
        .group_by(StockTransferItem.product_id)
        .all()
    )
    return {pid: max(int(qty or 0), 0) for pid, qty in rows if pid is not None}


def _supplier_lead_by_product(db: Session) -> Dict[int, int]:
    """Shortest supplier lead time per product (be optimistic: pick the
    fastest supplier that can restock the SKU)."""
    rows = (
        db.query(
            SupplierProduct.product_id,
            func.min(SupplierProduct.lead_time_days),
        )
        .filter(SupplierProduct.lead_time_days.isnot(None))
        .group_by(SupplierProduct.product_id)
        .all()
    )
    return {pid: int(days) for pid, days in rows if pid is not None and days is not None}


def _days_cover(units: float, velocity: float) -> float:
    """Forward days of cover; capped so an effectively-infinite cover
    serializes cleanly instead of as inf."""
    if velocity <= 0:
        return 999.0
    return round(units / velocity, 1)


def build_replenishment_plan(
    db: Session,
    *,
    velocity_window_days: int = 30,
    full_transfer_lead_days: int = DEFAULT_FULL_TRANSFER_LEAD_DAYS,
    target_cover_days: int = 30,
    limit: int = 200,
    today: Optional[date] = None,
) -> ReplenishmentReport:
    """Build the per-SKU replenishment plan.

    `target_cover_days` is how many days of forward cover a restock should
    aim to leave on the shelf *after* the relevant lead time elapses.
    """
    today = today or datetime.now(timezone.utc).date()
    cutoff = datetime.utcnow() - timedelta(days=velocity_window_days)

    velocity_by_product = _ml_velocity_by_product(db, cutoff, velocity_window_days)
    internal_by_product = _on_hand_at(db, LOCATION_INTERNAL)
    full_by_product = _on_hand_at(db, LOCATION_ML_FULL)
    in_transit_by_product = _in_transit_to_full(db)
    supplier_lead_by_product = _supplier_lead_by_product(db)

    # Only SKUs with ML velocity can deplete Full, so only they need a plan.
    candidate_ids = [pid for pid, v in velocity_by_product.items() if v > 0]
    products = (
        {p.id: p for p in db.query(Product).filter(Product.id.in_(candidate_ids)).all()}
        if candidate_ids
        else {}
    )

    rows: list[ReplenishmentRow] = []
    for pid in candidate_ids:
        product = products.get(pid)
        if product is None or getattr(product, "is_bundle", False):
            continue
        velocity = velocity_by_product[pid]

        internal = internal_by_product.get(pid, 0)
        full_on_hand = full_by_product.get(pid, 0)
        in_transit = in_transit_by_product.get(pid, 0)
        full_available = full_on_hand + in_transit
        pipeline = internal + full_available

        days_cover_full = _days_cover(full_available, velocity)
        days_cover_pipeline = _days_cover(pipeline, velocity)

        # --- Stage 2: internal -> Full ---------------------------------
        # Aim to leave Full covered for the transfer lead + target cover.
        target_full = math.ceil(velocity * (full_transfer_lead_days + target_cover_days))
        send_need = max(target_full - full_available, 0)
        send_to_full_qty = min(send_need, internal)
        send_to_full_by: Optional[date] = None
        if send_need > 0:
            # Ship before Full cover falls below the transfer lead time.
            days_until = max(int(days_cover_full) - full_transfer_lead_days, 0)
            send_to_full_by = today + timedelta(days=days_until)

        # --- Stage 1: supplier -> internal -----------------------------
        supplier_lead = supplier_lead_by_product.get(pid, DEFAULT_SUPPLIER_LEAD_DAYS)
        target_pipeline = math.ceil(velocity * (supplier_lead + target_cover_days))
        reorder_need = max(target_pipeline - pipeline, 0)
        reorder_qty = 0
        reorder_by: Optional[date] = None
        if reorder_need > 0:
            reorder_qty = (
                int(product.reorder_quantity)
                if product.reorder_quantity is not None
                else reorder_need
            )
            days_until = max(int(days_cover_pipeline) - supplier_lead, 0)
            reorder_by = today + timedelta(days=days_until)

        # Skip SKUs with nothing to do.
        if send_need <= 0 and reorder_need <= 0 and full_available > 0:
            continue

        if full_available <= 0:
            severity = "critical"  # out of Full now — losing buy-box
        elif (send_to_full_by is not None and send_to_full_by <= today) or (
            reorder_by is not None and reorder_by <= today
        ):
            severity = "soon"  # an action is due today
        elif (
            (send_to_full_by is not None and send_to_full_by <= today + timedelta(days=7))
            or (reorder_by is not None and reorder_by <= today + timedelta(days=7))
        ):
            severity = "watch"  # action falls due within a week
        else:
            severity = "ok"

        rows.append(
            ReplenishmentRow(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                supplier_id=product.supplier_id,
                daily_velocity=round(velocity, 2),
                internal_on_hand=internal,
                full_on_hand=full_on_hand,
                in_transit_to_full=in_transit,
                full_available=full_available,
                days_cover_full=days_cover_full,
                days_cover_pipeline=days_cover_pipeline,
                send_to_full_qty=send_to_full_qty,
                send_to_full_by=send_to_full_by,
                supplier_lead_time_days=supplier_lead_by_product.get(pid),
                reorder_qty=reorder_qty,
                reorder_by=reorder_by,
                severity=severity,
            )
        )

    # Most urgent first: by severity, then earliest action date.
    severity_order = {"critical": 0, "soon": 1, "watch": 2, "ok": 3}

    def _earliest_action(row: ReplenishmentRow) -> date:
        candidates = [d for d in (row.send_to_full_by, row.reorder_by) if d is not None]
        return min(candidates) if candidates else date.max

    rows.sort(key=lambda r: (severity_order.get(r.severity, 9), _earliest_action(r)))

    return ReplenishmentReport(
        rows=rows[:limit],
        velocity_window_days=velocity_window_days,
        full_transfer_lead_days=full_transfer_lead_days,
        target_cover_days=target_cover_days,
        total_send_now=sum(
            1 for r in rows if r.send_to_full_by is not None and r.send_to_full_by <= today
        ),
        total_reorder_now=sum(
            1 for r in rows if r.reorder_by is not None and r.reorder_by <= today
        ),
    )
