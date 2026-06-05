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
from sqlalchemy.orm import Session, contains_eager, joinedload

from src.api import dependencies
from src.core.errors import LocalizedHTTPException
from src.database import get_db
from src.models.order import (
    AmazonOrderRefund,
    OrderCostBreakdown,
    SalesOrder,
    SalesOrderItem,
)
from src.models.product import Product
from src.models.user import User
from src.services import marketplace_catalog
from src.schemas.sales_order import (
    OrderCostBreakdownRead,
    OrderRefundEventRead,
    OrderStatusEventRead,
    SalesOrder as SalesOrderSchema,
    SalesOrderChannelBreakdown,
    SalesOrderCreate,
    SalesOrderDetail,
    SalesOrderFulfillmentRead,
    SalesOrderItem as SalesOrderItemSchema,
    SalesOrderListResponse,
    SalesOrderCancelResult,
    SalesOrderReturnCreate,
    SalesOrderReturnRead,
    SalesOrderShippingChargeUpdate,
    SalesOrderShippingLabelUpdate,
    SalesOrderSummary,
)
from src.services.inventory_service import InsufficientStockError
from src.services.order_creation import create_onsite_order
from src.services.order_lifecycle import apply_status_change
from src.services.report_export import (
    ReportColumn,
    ReportTable,
    fmt_currency,
    fmt_date,
    fmt_int,
    fmt_percent,
    stream_csv,
    stream_pdf,
)

router = APIRouter()


# Allowlisted sortable columns for the list endpoint. Maps the public
# `sort_by` token → the SQLAlchemy column to order on. `net_margin_percent`
# lives on the 1:1 OrderCostBreakdown (joined below), so margin sorting is
# N+1-safe and NULL margins (no breakdown / zero-revenue) sort last in both
# directions via `.nullslast()`.
_SORT_COLUMNS = {
    "created_at": SalesOrder.created_at,
    "total_price": SalesOrder.total_price,
    "status": SalesOrder.status,
    "source": SalesOrder.source,
    "external_order_id": SalesOrder.external_order_id,
    "net_margin_percent": OrderCostBreakdown.net_margin_percent,
}
_DEFAULT_SORT_BY = "created_at"
_DEFAULT_SORT_DIR = "desc"


def _serialize_order(order: SalesOrder) -> SalesOrderSchema:
    # Margin is read from the 1:1 cost breakdown. None when the order has
    # no breakdown row, or when the breakdown's net_margin_percent is NULL
    # (zero-revenue order). The list query eager-loads `cost_breakdown`
    # (joinedload) and the detail endpoint already does too, so this never
    # triggers an N+1.
    margin = (
        order.cost_breakdown.net_margin_percent
        if order.cost_breakdown is not None
        else None
    )
    return SalesOrderSchema(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        currency=order.currency,
        created_at=order.created_at,
        # `source` is a plain string column now (catalog-governed).
        source=order.source,
        external_order_id=order.external_order_id,
        net_margin_percent=margin,
    )


def _serialize_order_detail(order: SalesOrder) -> SalesOrderDetail:
    """Build the full `SalesOrderDetail` for a single order. Shared by the
    GET detail endpoint and the POST create endpoint so both return the
    identical shape. `order.items` must be loaded; cost breakdown / status
    timeline / refund events are surfaced when present (a freshly-created
    on-site order has items but no breakdown/timeline/refunds yet)."""
    items: List[SalesOrderItemSchema] = []
    for item in order.items:
        product: Optional[Product] = item.product
        items.append(
            SalesOrderItemSchema(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_per_unit=item.price_per_unit,
                cost_per_unit=item.cost_per_unit,
                product_name=product.name if product else None,
                product_sku=product.sku if product else None,
            )
        )

    breakdown: Optional[OrderCostBreakdownRead] = (
        OrderCostBreakdownRead.model_validate(order.cost_breakdown)
        if order.cost_breakdown is not None
        else None
    )
    timeline = [OrderStatusEventRead.model_validate(ev) for ev in order.status_events]

    base = _serialize_order(order)
    return SalesOrderDetail(
        **base.model_dump(),
        items=items,
        cost_breakdown=breakdown,
        status_timeline=timeline,
        refund_events=[],
    )


def _serialize_fulfillment(order: SalesOrder) -> SalesOrderFulfillmentRead:
    return SalesOrderFulfillmentRead(
        order_id=order.id,
        shipping_rate_id=order.shipping_rate_id,
        shipping_provider=order.shipping_provider,
        shipping_carrier=order.shipping_carrier,
        shipping_service=order.shipping_service,
        shipping_cost=order.shipping_cost,
        shipping_currency=order.shipping_currency,
        shipping_estimated_days=order.shipping_estimated_days,
        shipping_charge_idempotency_key=order.shipping_charge_idempotency_key,
        shipping_shipment_id=order.shipping_shipment_id,
        shipping_tracking_number=order.shipping_tracking_number,
        shipping_label_url=order.shipping_label_url,
        shipping_tracking_url=order.shipping_tracking_url,
        shipping_label_idempotency_key=order.shipping_label_idempotency_key,
    )


def _get_order_or_404(db: Session, order_id: int) -> SalesOrder:
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not order:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrder.notFound",
            params={"id": order_id},
            detail="Sales order not found",
        )
    return order


@router.post("/", status_code=201, response_model=SalesOrderDetail)
def create_sales_order(
    *,
    db: Session = Depends(dependencies.get_db),
    payload: SalesOrderCreate,
    # Accept EITHER a JWT (admin/POS UI) OR an X-API-Key (the storefront BFF,
    # server-to-server). `get_current_user_with_api_key` resolves both and
    # prefers the API key when present.
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """Create an on-site (point-of-sale) sales order.

    Authenticated. The server prices each line authoritatively from the
    product/variant (the request carries no prices), decrements stock
    atomically per line, and persists the order all-or-nothing: if any
    line lacks stock NO order is created and no stock moves.

    Idempotent on `idempotency_key` — a retry with the same key returns
    the already-created order (still 201) without decrementing stock
    again.

    Uses the request-scoped committing `get_db` (`dependencies.get_db`):
    it commits on success and rolls back on any exception, so a
    propagated `InsufficientStockError` reverts the whole request.
    """
    try:
        order, _created = create_onsite_order(db, payload, user_id=current_user.id)
    except InsufficientStockError as exc:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.inventory.insufficientStock",
            params={"key": payload.idempotency_key},
            detail=str(exc),
        )

    # Re-fetch with relationships eager-loaded so the response serializer
    # sees the items (and any product names) without lazy N+1 loads.
    order = (
        db.query(SalesOrder)
        .options(
            joinedload(SalesOrder.items).joinedload(SalesOrderItem.product),
            joinedload(SalesOrder.cost_breakdown),
            joinedload(SalesOrder.status_events),
        )
        .filter(SalesOrder.id == order.id)
        .one()
    )
    return _serialize_order_detail(order)


@router.put("/{order_id}/shipping-charge", response_model=SalesOrderFulfillmentRead)
def update_sales_order_shipping_charge(
    *,
    order_id: int,
    payload: SalesOrderShippingChargeUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """Persist the selected storefront shipping charge on the order.

    Authenticated via the same JWT-or-API-key dependency as on-site order
    creation. Retries with the same idempotency key return the persisted
    fulfillment snapshot without reapplying anything. A new quote can replace
    a previous one until a label has been attached.
    """
    order = _get_order_or_404(db, order_id)

    if order.shipping_charge_idempotency_key == payload.idempotency_key:
        return _serialize_fulfillment(order)

    if order.shipping_label_idempotency_key:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.salesOrder.shippingLabelAlreadyCreated",
            params={"id": order_id},
            detail="Cannot change shipping charge after a label is attached",
        )

    order.shipping_rate_id = payload.rate_id
    order.shipping_provider = payload.provider
    order.shipping_carrier = payload.carrier
    order.shipping_service = payload.service
    order.shipping_cost = payload.amount_cents / 100.0
    order.shipping_currency = payload.currency.upper()
    order.shipping_estimated_days = payload.estimated_days
    order.shipping_charge_idempotency_key = payload.idempotency_key

    db.flush()
    return _serialize_fulfillment(order)


@router.put("/{order_id}/shipping-label", response_model=SalesOrderFulfillmentRead)
def update_sales_order_shipping_label(
    *,
    order_id: int,
    payload: SalesOrderShippingLabelUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """Attach purchased shipping-label metadata to the Fulcrum order.

    Label creation is treated as one-way for idempotency: the same key is a
    safe retry, while a different key after a stored label is rejected so a
    second purchased label cannot overwrite the first one accidentally.
    """
    order = _get_order_or_404(db, order_id)

    if order.shipping_label_idempotency_key == payload.idempotency_key:
        return _serialize_fulfillment(order)

    if order.shipping_label_idempotency_key:
        raise LocalizedHTTPException(
            status_code=409,
            code="apiErrors.salesOrder.shippingLabelAlreadyCreated",
            params={"id": order_id},
            detail="Shipping label already attached to this order",
        )

    order.shipping_provider = payload.provider
    order.shipping_carrier = payload.carrier
    order.shipping_shipment_id = payload.shipment_id
    order.shipping_tracking_number = payload.tracking_number
    order.shipping_label_url = payload.label_url
    order.shipping_tracking_url = payload.tracking_url
    order.shipping_label_idempotency_key = payload.idempotency_key

    db.flush()
    return _serialize_fulfillment(order)


@router.get("/", response_model=SalesOrderListResponse)
def list_sales_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    source: Optional[str] = Query(
        None, description="Filter by channel (order source, e.g. MERCADOLIBRE)"
    ),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: Optional[int] = Query(
        None, ge=1, le=365, description="Only orders from the last N days"
    ),
    search: Optional[str] = Query(
        None,
        description="Case-insensitive substring match on external_order_id",
    ),
    sort_by: str = Query(
        _DEFAULT_SORT_BY,
        description=(
            "Column to sort by. One of: created_at, total_price, status, "
            "source, external_order_id, net_margin_percent. Unknown values "
            "fall back to created_at."
        ),
    ),
    sort_dir: str = Query(
        _DEFAULT_SORT_DIR,
        description="Sort direction: 'asc' or 'desc'. Unknown falls back to desc.",
    ),
    skip: int = 0,
    limit: int = Query(100, le=500),
):
    """List sales orders as a paged envelope `{items, total, skip, limit}`.

    Optionally filtered by channel, status, recency, and a case-insensitive
    substring `search` on the external order id. All filters AND-compose.
    `total` is the count of matching rows BEFORE skip/limit so the UI can
    drive a server-side paginator.

    Sortable via `sort_by` (allowlisted) + `sort_dir` (asc/desc); invalid
    input safely falls back to the `created_at desc` default. `SalesOrder.id`
    is always appended as a stable tiebreaker and NULLs sort last.
    """
    # Validate against the allowlist; invalid values fall back to the safe
    # default rather than 400, matching the lenient string filters above.
    sort_col = _SORT_COLUMNS.get(sort_by, _SORT_COLUMNS[_DEFAULT_SORT_BY])
    direction = (
        sort_dir.lower() if sort_dir.lower() in {"asc", "desc"} else _DEFAULT_SORT_DIR
    )

    q = db.query(SalesOrder)
    if source is not None:
        q = q.filter(SalesOrder.source == source.strip().upper())
    if status is not None:
        q = q.filter(SalesOrder.status == status)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(SalesOrder.created_at >= cutoff)
    if search is not None and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.filter(func.lower(SalesOrder.external_order_id).like(term))

    # Count BEFORE offset/limit — and BEFORE the joinedload so the 1:1
    # LEFT JOIN can't perturb the count (it can't fan out, but counting on
    # the bare filtered query keeps the intent explicit).
    total = q.count()

    # When sorting on the margin (cost_breakdown) column, the joinedload's
    # implicit LEFT JOIN isn't usable in ORDER BY, so add an explicit
    # outerjoin to the same relationship. `contains_eager` reuses that join
    # to hydrate `cost_breakdown` without a second query (still N+1-safe).
    primary = sort_col.asc() if direction == "asc" else sort_col.desc()
    if sort_by == "net_margin_percent":
        rows = (
            q.outerjoin(OrderCostBreakdown, SalesOrder.cost_breakdown)
            .options(contains_eager(SalesOrder.cost_breakdown))
            .order_by(primary.nullslast(), SalesOrder.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        rows = (
            q.options(joinedload(SalesOrder.cost_breakdown))
            .order_by(primary.nullslast(), SalesOrder.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    return SalesOrderListResponse(
        items=[_serialize_order(o) for o in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


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
        by_channel.append(
            SalesOrderChannelBreakdown(
                source=str(source_value),
                count=count,
                revenue=float(revenue or 0.0),
            )
        )
        total_orders += count
        total_revenue += float(revenue or 0.0)

    # Ensure each catalog channel appears, even with zero, so the widget
    # renders a stable axis — and a marketplace added to the catalog
    # shows up here automatically.
    seen = {row.source for row in by_channel}
    for channel in marketplace_catalog.order_sources():
        if channel not in seen:
            by_channel.append(
                SalesOrderChannelBreakdown(source=channel, count=0, revenue=0.0)
            )

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
    "AMAZON": "Amazon",
    "FULCRUM": "Fulcrum",
}


def _channel_summary_rows(summary: SalesOrderSummary) -> list[dict]:
    """Flatten the SalesOrderSummary into one dict per channel, with a
    pre-computed `share` percentage so the export can show channel mix
    without re-deriving it client-side."""
    total = summary.total_revenue or 0.0
    rows: list[dict] = []
    for row in summary.by_channel:
        share = (row.revenue / total * 100.0) if total > 0 else 0.0
        rows.append(
            {
                "channel": _CHANNEL_LABELS.get(row.source, row.source),
                "orders": row.count,
                "revenue": row.revenue,
                "share": share,
            }
        )
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
            ReportColumn("orders", "Orders", align="right", formatter=fmt_int),
            ReportColumn("revenue", "Revenue", align="right", formatter=fmt_currency),
            ReportColumn("share", "Share", align="right", formatter=fmt_percent),
        ],
        rows=_channel_summary_rows(summary),
    )


# --- List export (per-order) ------------------------------------------------


def _build_sales_order_export_rows(
    db: Session,
    *,
    source: Optional[str],
    status: Optional[str],
    days: Optional[int],
    search: Optional[str],
    limit: int,
) -> list[dict]:
    q = db.query(SalesOrder)
    if source is not None:
        q = q.filter(SalesOrder.source == source.strip().upper())
    if status is not None:
        q = q.filter(SalesOrder.status == status)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(SalesOrder.created_at >= cutoff)
    # Same external-id substring as the JSON list, so an export matches the
    # on-screen search scope (WYSIWYG).
    if search is not None and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.filter(func.lower(SalesOrder.external_order_id).like(term))
    q = q.order_by(SalesOrder.created_at.desc().nullslast(), SalesOrder.id.desc())

    rows: list[dict] = []
    for o in q.limit(limit).all():
        rows.append(
            {
                "order_id": o.id,
                "channel": _CHANNEL_LABELS.get(o.source, o.source) if o.source else "",
                "external_order_id": o.external_order_id or "",
                "status": o.status or "",
                "total_price": float(o.total_price or 0.0),
                "created_at": o.created_at,
            }
        )
    return rows


def _sales_order_export_table(rows: list[dict]) -> ReportTable:
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = sum(r["total_price"] for r in rows)
    return ReportTable(
        title="Fulcrum — Sales Orders",
        subtitle=(
            f"Generated {date_stamp} · {len(rows)} orders · total value ${total:,.2f}"
        ),
        filename_stem="fulcrum-sales-orders",
        empty_message="No sales orders match the filters.",
        columns=[
            ReportColumn("order_id", "Order ID", align="right", formatter=fmt_int),
            ReportColumn("channel", "Channel"),
            ReportColumn("external_order_id", "External ID"),
            ReportColumn("status", "Status"),
            ReportColumn("total_price", "Total", align="right", formatter=fmt_currency),
            ReportColumn("created_at", "Created", formatter=fmt_date),
        ],
        rows=rows,
    )


@router.get("/export")
def export_sales_orders_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    search: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
) -> StreamingResponse:
    """Stream the sales orders list as a CSV. Same filters as the JSON
    list endpoint; default limit 5000 (cap 10000) for the "give me
    everything in this quarter" use case."""
    rows = _build_sales_order_export_rows(
        db,
        source=source,
        status=status,
        days=days,
        search=search,
        limit=limit,
    )
    return stream_csv(_sales_order_export_table(rows))


@router.get("/export-pdf")
def export_sales_orders_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    search: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
) -> StreamingResponse:
    rows = _build_sales_order_export_rows(
        db,
        source=source,
        status=status,
        days=days,
        search=search,
        limit=limit,
    )
    return stream_pdf(_sales_order_export_table(rows))


# --- Channel summary export (existing) --------------------------------------


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
    """Get a single sales order with the full picture: line items (with
    per-line cost), the cost/fee/margin breakdown, the status timeline,
    and any Amazon partial-refund events."""
    order = (
        db.query(SalesOrder)
        .options(
            joinedload(SalesOrder.items).joinedload(SalesOrderItem.product),
            joinedload(SalesOrder.cost_breakdown),
            joinedload(SalesOrder.status_events),
        )
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
                cost_per_unit=item.cost_per_unit,
                product_name=product.name if product else None,
                product_sku=product.sku if product else None,
            )
        )

    # Cost/fee/margin breakdown (1:1, may be absent on un-computed orders).
    breakdown: Optional[OrderCostBreakdownRead] = (
        OrderCostBreakdownRead.model_validate(order.cost_breakdown)
        if order.cost_breakdown is not None
        else None
    )

    # Status timeline, oldest → newest (relationship is order_by changed_at).
    timeline = [OrderStatusEventRead.model_validate(ev) for ev in order.status_events]

    # Amazon partial-refund events for this order, newest first.
    refunds = (
        db.query(AmazonOrderRefund)
        .filter(AmazonOrderRefund.order_id == order.id)
        .order_by(AmazonOrderRefund.posted_at.desc().nullslast())
        .all()
    )
    refund_events = [
        OrderRefundEventRead(
            refund_id=r.amazon_refund_id,
            posted_at=r.posted_at,
            refund_amount=float(r.refund_amount or 0.0),
            currency=r.currency,
        )
        for r in refunds
    ]

    base = _serialize_order(order)
    return SalesOrderDetail(
        **base.model_dump(),
        items=items,
        cost_breakdown=breakdown,
        status_timeline=timeline,
        refund_events=refund_events,
    )


# ---------------------------------------------------------------------------
# Cancellation (operator / BFF compensation)
# ---------------------------------------------------------------------------


@router.post("/{order_id}/cancel", response_model=SalesOrderCancelResult)
def cancel_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    # JWT (admin/POS) OR X-API-Key (storefront BFF, server-to-server). The BFF
    # calls this to compensate a capture failure after order-create — cancel the
    # order so its stock is released. Mirrors order-create's dual auth (FP-04).
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """Cancel a sales order; re-credit stock if it was cancelled before shipping.

    Delegates to `order_lifecycle.apply_status_change` (the same transition the
    marketplace pollers/webhooks use), which writes the audit row and, on a
    realized→CANCELLED transition for an unshipped order, re-credits stock
    exactly once (guarded by `stock_recredited_at`).

    **Idempotent:** cancelling an already-cancelled order is a no-op and still
    returns 200 — so the BFF's compensation retry is safe (no double credit).
    """
    order = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.items))
        .filter(SalesOrder.id == order_id)
        .first()
    )
    if order is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrder.notFound",
            params={"id": order_id},
            detail="Sales order not found",
        )

    apply_status_change(
        db, order, new_status="CANCELLED", source_signal="manual"
    )
    db.commit()
    db.refresh(order)
    return SalesOrderCancelResult(
        id=order.id,
        status=order.status,
        stock_recredited=order.stock_recredited_at is not None,
    )


# ---------------------------------------------------------------------------
# Returns workflow
# ---------------------------------------------------------------------------


def _load_order_or_404(db: Session, order_id: int) -> SalesOrder:
    """Shared order lookup for the returns endpoints. Eager-loads
    `items` because the service needs to validate `order_item_id`
    membership and grab `product_id` when only the item id was sent.
    """
    order = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.items))
        .filter(SalesOrder.id == order_id)
        .first()
    )
    if order is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.salesOrder.notFound",
            params={"id": order_id},
            detail="Sales order not found",
        )
    return order


def _serialize_return(ret) -> SalesOrderReturnRead:
    """Hydrate a `SalesOrderReturn` row into its read schema, joining
    in product name/sku + recorder email so the UI doesn't need a
    follow-up call per row."""
    product = ret.product
    return SalesOrderReturnRead(
        id=ret.id,
        order_id=ret.order_id,
        order_item_id=ret.order_item_id,
        product_id=ret.product_id,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        quantity=ret.quantity,
        received_at=ret.received_at,
        recorded_by_user_id=ret.recorded_by_user_id,
        # The relationship isn't eager-loaded on the list query
        # (it's a single FK per row; lazy is fine), but we use it
        # opportunistically to surface the recorder's email.
        recorded_by_email=None,  # filled by the endpoint below when available
        reason=ret.reason,
        notes=ret.notes,
    )


@router.post(
    "/{order_id}/returns",
    response_model=List[SalesOrderReturnRead],
    status_code=201,
)
def record_sales_order_return(
    order_id: int,
    payload: SalesOrderReturnCreate,
    db: Session = Depends(get_db),
    # Accept EITHER a JWT (admin/POS UI) OR an X-API-Key (the storefront BFF,
    # server-to-server returns/refund flow). Mirrors order-create (FP-04):
    # `get_current_user_with_api_key` resolves both and prefers the API key.
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """Record one or more physical returns against a sales order.

    For each line: persists a `SalesOrderReturn` row + credits the
    quantity back to inventory with `reason_code='return'`. Returns
    the newly-created rows so the UI can append them to the
    on-screen history without a follow-up GET.
    """
    from src.services.sales_order_returns import (
        ReturnLineInput,
        record_return as svc_record,
    )

    order = _load_order_or_404(db, order_id)
    lines = [
        ReturnLineInput(
            order_item_id=line.order_item_id,
            product_id=line.product_id,
            quantity=line.quantity,
        )
        for line in payload.lines
    ]
    created = svc_record(
        db,
        order=order,
        lines=lines,
        reason=payload.reason,
        notes=payload.notes,
        actor=current_user,
    )
    db.commit()
    # Refresh so `product` relationship is populated for the response.
    for ret in created:
        db.refresh(ret)

    rows: List[SalesOrderReturnRead] = []
    for ret in created:
        out = _serialize_return(ret)
        # The endpoint knows who recorded it (current_user); save a
        # roundtrip by surfacing the email here.
        if current_user and current_user.email:
            out.recorded_by_email = current_user.email
        rows.append(out)
    return rows


@router.get(
    "/{order_id}/returns",
    response_model=List[SalesOrderReturnRead],
)
def list_sales_order_returns(
    order_id: int,
    db: Session = Depends(get_db),
    # Same dual auth as record (JWT or X-API-Key) so the BFF can read back too.
    current_user: User = Depends(dependencies.get_current_user_with_api_key),
):
    """List all return events recorded for an order, newest first."""
    from src.models.user import User as UserModel
    from src.services.sales_order_returns import list_returns as svc_list

    order = _load_order_or_404(db, order_id)
    returns = svc_list(db, order)

    # Resolve recorder emails in one extra query to avoid N+1.
    user_ids = {r.recorded_by_user_id for r in returns if r.recorded_by_user_id}
    emails: dict[int, str] = {}
    if user_ids:
        for uid, email in (
            db.query(UserModel.id, UserModel.email)
            .filter(UserModel.id.in_(user_ids))
            .all()
        ):
            emails[uid] = email

    rows: List[SalesOrderReturnRead] = []
    for ret in returns:
        out = _serialize_return(ret)
        if ret.recorded_by_user_id is not None:
            out.recorded_by_email = emails.get(ret.recorded_by_user_id)
        rows.append(out)
    return rows
