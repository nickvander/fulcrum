"""On-site (point-of-sale) order creation — FP-04.

The marketplace channels (Amazon / MercadoLibre) create `SalesOrder`
rows by ingesting an external order whose price + status the marketplace
already decided. An on-site order is the inverse: WE are the authority.
The operator sends product ids + quantities, the server prices each line
from the product/variant, decrements stock atomically per line via
`InventoryService.decrement_stock_atomic` (FP-03), and persists the order
+ items in ONE transaction.

Three guarantees, layered here:

  * **Idempotent** — the request's `idempotency_key` is stored as the
    order's `external_order_id` (with `source=FULCRUM`). A retry with the
    same key returns the already-created order and does NOT re-decrement
    stock.
  * **Authoritative pricing** — `price_per_unit` is read from the variant
    (`ProductVariant.price`) when a `variant_id` is given, else from the
    product (`Product.default_resale_price`). The request never carries a
    price.
  * **All-or-nothing** — the order row, its items, and every line's stock
    decrement live in one SAVEPOINT. If ANY line can't be satisfied,
    `decrement_stock_atomic` raises `InsufficientStockError`, the
    SAVEPOINT rolls back, and neither the order nor any earlier line's
    decrement survives. See the comment on the `begin_nested()` block.
"""
from __future__ import annotations

from datetime import datetime
from typing import Tuple

from sqlalchemy.orm import Session

from src.core.errors import LocalizedHTTPException
from src.models.inventory import InventoryAdjustmentReasonCode
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.models.product import Product
from src.models.product_variant import ProductVariant
from src.schemas.sales_order import SalesOrderCreate
from src.services.inventory_service import inventory_service


# Initial status for a paid, fulfilled-at-the-counter order. On-site sales
# are realized revenue the instant they happen — money + goods both change
# hands at the counter — so the order lands in the realized set the reports
# treat as final (`calculate_sales_velocity` filters status IN
# ("COMPLETED", "SHIPPED")) rather than the "open" set the dashboard
# summary counts (PENDING / PROCESSING / CONFIRMED / PAID). Upper-cased to
# match the cross-channel convention the marketplace ingesters established.
ONSITE_ORDER_STATUS = "COMPLETED"


class _ResolvedLine:
    """Internal: a request line with its server-resolved price/cost,
    captured in pass 1 so pass 2 can persist items + decrement stock
    without re-querying the product."""

    __slots__ = ("product_id", "variant_id", "quantity", "price_per_unit", "cost_per_unit")

    def __init__(self, product_id, variant_id, quantity, price_per_unit, cost_per_unit):
        self.product_id = product_id
        self.variant_id = variant_id
        self.quantity = quantity
        self.price_per_unit = price_per_unit
        self.cost_per_unit = cost_per_unit


def _resolve_price_per_unit(product: Product, variant: ProductVariant | None) -> float:
    """Authoritative per-unit price: the variant's price override when a
    variant was selected, otherwise the product's default resale price.
    Falls back to 0.0 when neither is set so the line still prices (a
    NULL price would otherwise make `total_price` NULL)."""
    if variant is not None and variant.price is not None:
        return float(variant.price)
    if product.default_resale_price is not None:
        return float(product.default_resale_price)
    return 0.0


def create_onsite_order(
    db: Session, payload: SalesOrderCreate, user_id: int
) -> Tuple[SalesOrder, bool]:
    """Create (or idempotently return) an on-site sales order.

    Returns ``(order, created)`` where ``created`` is False when an order
    with this `idempotency_key` already existed — in that case nothing is
    written and no stock moves.

    Raises:
      * :class:`LocalizedHTTPException` (404, ``apiErrors.product.notFound``)
        if any line references a missing product.
      * :class:`~src.services.inventory_service.InsufficientStockError`
        (propagated from `decrement_stock_atomic`) if any line lacks stock.

    Does NOT commit — the request-scoped `get_db` commits on success and
    rolls back on any exception.
    """
    # --- Idempotency: same key + FULCRUM source ⇒ return the existing order.
    # We compare against OrderSource.FULCRUM.value to match the plain-string
    # `source` column exactly (the enum subclasses str, but being explicit
    # keeps the SQL bind unambiguous).
    existing = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.source == OrderSource.FULCRUM.value,
            SalesOrder.external_order_id == payload.idempotency_key,
        )
        .first()
    )
    if existing is not None:
        return existing, False

    # Guard non-empty items even though the schema enforces it — the
    # service must be safe to call directly (tests, future callers).
    if not payload.items:
        raise LocalizedHTTPException(
            status_code=422,
            code="apiErrors.salesOrder.emptyItems",
            detail="A sales order must contain at least one line item.",
        )

    # Everything below — the order row, its items, and every line's stock
    # decrement — runs inside ONE SAVEPOINT. `decrement_stock_atomic`
    # raises `InsufficientStockError` the moment a line can't be satisfied;
    # that propagates out of this `with` block, the SAVEPOINT rolls back,
    # and the order + items + any EARLIER lines' decrements are all
    # reverted together. That is the all-or-nothing guarantee. The outer
    # request transaction (committed by `get_db`) then either commits the
    # whole order or, on a propagated exception, rolls the request back.
    with db.begin_nested():
        total_price = 0.0
        resolved: list[_ResolvedLine] = []

        for line in payload.items:
            product = (
                db.query(Product).filter(Product.id == line.product_id).first()
            )
            if product is None:
                raise LocalizedHTTPException(
                    status_code=404,
                    code="apiErrors.product.notFound",
                    params={"id": line.product_id},
                    detail=f"Product {line.product_id} not found",
                )

            variant: ProductVariant | None = None
            if line.variant_id is not None:
                variant = (
                    db.query(ProductVariant)
                    .filter(ProductVariant.id == line.variant_id)
                    .first()
                )

            price_per_unit = _resolve_price_per_unit(product, variant)
            # Snapshot cost-at-sale so the margin report doesn't drift when
            # the product/variant cost is later changed (same rationale as
            # the marketplace ingesters). Prefer the variant's cost when a
            # variant was sold; fall back to the product's.
            cost_per_unit = None
            if variant is not None and variant.cost_price is not None:
                cost_per_unit = float(variant.cost_price)
            elif product.cost_price is not None:
                cost_per_unit = float(product.cost_price)

            total_price += price_per_unit * line.quantity
            resolved.append(
                _ResolvedLine(
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    quantity=line.quantity,
                    price_per_unit=price_per_unit,
                    cost_per_unit=cost_per_unit,
                )
            )

        order = SalesOrder(
            status=ONSITE_ORDER_STATUS,
            total_price=total_price,
            currency=payload.currency,
            source=OrderSource.FULCRUM.value,
            external_order_id=payload.idempotency_key,
            created_at=datetime.utcnow(),
        )
        db.add(order)
        db.flush()  # populate order.id for the line items below

        for r in resolved:
            db.add(
                SalesOrderItem(
                    order_id=order.id,
                    product_id=r.product_id,
                    quantity=r.quantity,
                    price_per_unit=r.price_per_unit,
                    cost_per_unit=r.cost_per_unit,
                )
            )
            # Atomic, guarded decrement. RAISES InsufficientStockError if
            # this line can't be satisfied — we let it propagate so the
            # SAVEPOINT (and request) rolls back, reverting the order +
            # earlier lines. No oversell, no negative stock (FP-03).
            inventory_service.decrement_stock_atomic(
                db,
                product_id=r.product_id,
                quantity=r.quantity,
                variant_id=r.variant_id,
                location=payload.location,
                reason="on-site order",
                reason_code=InventoryAdjustmentReasonCode.SALE,
                user_id=str(user_id),
            )

    return order, True
