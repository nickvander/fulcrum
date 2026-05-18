"""
Sales orders API.

Sales orders are created by:
- Marketplace webhook handlers (MercadoLibre, Amazon) — see endpoints/webhooks.py
- Future on-site Stripe checkout (Phase 7)

This module exposes read-only listing, detail, and channel summary endpoints
used by the dashboard and the Orders module.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.api import dependencies
from src.core.errors import LocalizedHTTPException
from src.database import get_db
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.models.user import User
from src.schemas.sales_order import (
    OrderSourceSchema,
    SalesOrder as SalesOrderSchema,
    SalesOrderChannelBreakdown,
    SalesOrderDetail,
    SalesOrderItem as SalesOrderItemSchema,
    SalesOrderSummary,
)
from src.services.report_export import (
    ReportColumn,
    ReportTable,
    fmt_currency,
    fmt_int,
    fmt_percent,
    stream_csv,
    stream_pdf,
)

router = APIRouter()


def _serialize_order(order: SalesOrder) -> SalesOrderSchema:
    return SalesOrderSchema(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        created_at=order.created_at,
        source=order.source.value if order.source else None,
        external_order_id=order.external_order_id,
    )


@router.get("/", response_model=List[SalesOrderSchema])
def list_sales_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    source: Optional[OrderSourceSchema] = Query(None, description="Filter by channel"),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Only orders from the last N days"),
    skip: int = 0,
    limit: int = Query(100, le=500),
):
    """List sales orders, optionally filtered by channel, status, or recency."""
    q = db.query(SalesOrder)
    if source is not None:
        q = q.filter(SalesOrder.source == OrderSource(source.value))
    if status is not None:
        q = q.filter(SalesOrder.status == status)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(SalesOrder.created_at >= cutoff)
    q = q.order_by(SalesOrder.created_at.desc().nullslast(), SalesOrder.id.desc())
    rows = q.offset(skip).limit(limit).all()
    return [_serialize_order(o) for o in rows]


@router.get("/summary", response_model=SalesOrderSummary)
def sales_order_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    days: int = Query(30, ge=1, le=365),
):
    """
    Channel breakdown for the dashboard 'Sales by Channel' widget.

    Open orders are counted across all-time, since 'open' isn't time-bounded
    the way revenue is.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            SalesOrder.source,
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_price), 0.0),
        )
        .filter(SalesOrder.created_at >= cutoff)
        .group_by(SalesOrder.source)
        .all()
    )

    by_channel: List[SalesOrderChannelBreakdown] = []
    total_orders = 0
    total_revenue = 0.0
    for source_value, count, revenue in rows:
        if source_value is None:
            continue
        source_str = source_value.value if hasattr(source_value, "value") else source_value
        by_channel.append(
            SalesOrderChannelBreakdown(
                source=OrderSourceSchema(source_str),
                count=count,
                revenue=float(revenue or 0.0),
            )
        )
        total_orders += count
        total_revenue += float(revenue or 0.0)

    # Ensure each known channel appears, even with zero, so the widget can render a stable axis.
    seen = {row.source for row in by_channel}
    for channel in OrderSourceSchema:
        if channel not in seen:
            by_channel.append(SalesOrderChannelBreakdown(source=channel, count=0, revenue=0.0))

    open_statuses = ["PENDING", "PROCESSING", "CONFIRMED", "PAID"]
    open_orders = (
        db.query(func.count(SalesOrder.id))
        .filter(SalesOrder.status.in_(open_statuses))
        .scalar()
        or 0
    )

    return SalesOrderSummary(
        window_days=days,
        total_orders=total_orders,
        total_revenue=total_revenue,
        open_orders=int(open_orders),
        by_channel=by_channel,
    )


# ---------------------------------------------------------------------------
# Exports (CSV + PDF) for the channel summary, via the shared report_export
# helpers. Both formats call the JSON summary first so the underlying data
# is identical regardless of file type.
# ---------------------------------------------------------------------------

# Pretty labels for OrderSource → channel column. Single source of truth
# shared with the dashboard widget (kept in sync manually for now).
_CHANNEL_LABELS = {
    "MERCADOLIBRE": "MercadoLibre",
    "AMAZON":       "Amazon",
    "FULCRUM":      "Fulcrum",
}


def _channel_summary_rows(summary: SalesOrderSummary) -> list[dict]:
    """Flatten the SalesOrderSummary into one dict per channel, with a
    pre-computed `share` percentage so the export can show channel mix
    without re-deriving it client-side."""
    total = summary.total_revenue or 0.0
    rows: list[dict] = []
    for row in summary.by_channel:
        share = (row.revenue / total * 100.0) if total > 0 else 0.0
        rows.append({
            "channel": _CHANNEL_LABELS.get(row.source.value, row.source.value),
            "orders": row.count,
            "revenue": row.revenue,
            "share": share,
        })
    # Stable ordering: highest revenue first, then alphabetical.
    rows.sort(key=lambda r: (-r["revenue"], r["channel"]))
    return rows


def _channel_summary_table(summary: SalesOrderSummary) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ReportTable(
        title="Fulcrum — Sales by Channel",
        subtitle=(
            f"Generated {date_stamp} · last {summary.window_days} days · "
            f"{summary.total_orders} orders · {summary.open_orders} open"
        ),
        filename_stem="fulcrum-sales-by-channel",
        empty_message="No sales recorded in this window.",
        columns=[
            ReportColumn("channel", "Channel"),
            ReportColumn("orders",  "Orders",  align="right", formatter=fmt_int),
            ReportColumn("revenue", "Revenue", align="right", formatter=fmt_currency),
            ReportColumn("share",   "Share",   align="right", formatter=fmt_percent),
        ],
        rows=_channel_summary_rows(summary),
    )


@router.get("/summary/export")
def export_summary_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    days: int = Query(30, ge=1, le=365),
) -> StreamingResponse:
    """Channel summary as a CSV. One row per channel + a `share` column with
    each channel's % of total revenue. Empty windows still produce a 200
    with the header row."""
    summary = sales_order_summary(db=db, current_user=current_user, days=days)
    return stream_csv(_channel_summary_table(summary))


@router.get("/summary/export-pdf")
def export_summary_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    days: int = Query(30, ge=1, le=365),
) -> StreamingResponse:
    """Channel summary as a printable PDF. Same shape as the CSV."""
    summary = sales_order_summary(db=db, current_user=current_user, days=days)
    return stream_pdf(_channel_summary_table(summary))


@router.get("/{order_id}", response_model=SalesOrderDetail)
def get_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """Get a single sales order with line items."""
    order = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.items).joinedload(SalesOrderItem.product))
        .filter(SalesOrder.id == order_id)
        .first()
    )
    if not order:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrder.notFound",
            params={"id": order_id},
            detail="Sales order not found",
        )

    items: List[SalesOrderItemSchema] = []
    for item in order.items:
        product: Optional[Product] = item.product
        items.append(
            SalesOrderItemSchema(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_per_unit=item.price_per_unit,
                product_name=product.name if product else None,
                product_sku=product.sku if product else None,
            )
        )

    base = _serialize_order(order)
    return SalesOrderDetail(**base.model_dump(), items=items)
