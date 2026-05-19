"""Coverage for `services/order_lifecycle.py` — status-event audit,
breakdown `reversed_at`, and cancel-before-ship stock re-credit.

The lifecycle hook is called from three ingestion paths (ML
webhook, ML poll, Amazon poll) so the contract has to be airtight
about: (1) no audit row when status didn't change; (2) reversed_at
flips both directions; (3) stock is re-credited iff the order was
never shipped + not already credited.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.crud import crud_product
from src.models.inventory import InventoryItem
from src.models.order import (
    OrderSource,
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatusEvent,
)
from src.schemas.product import ProductCreate
from src.services import order_cost_engine
from src.services.order_lifecycle import (
    apply_status_change,
    record_initial_status,
)


pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_order_with_inventory(
    db: Session, *, status: str = "PAID", sku: str = "LIFE-1", qty: int = 5,
) -> SalesOrder:
    """Create a realized order with one line item + matching inventory.
    Returns the order; caller can mutate it."""
    product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name=f"Lifecycle {sku}", sku=sku,
            default_resale_price=50.0, cost_price=20.0,
        ),
    )
    db.add(InventoryItem(product_id=product.id, quantity=100, location="default"))
    order = SalesOrder(
        status=status,
        total_price=qty * 50.0,
        currency="MXN",
        created_at=datetime.utcnow(),
        source=OrderSource.MERCADOLIBRE,
        external_order_id=f"EXT-{sku}",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, price_per_unit=50.0, cost_per_unit=20.0,
    ))
    db.commit()
    db.refresh(order)
    order_cost_engine.upsert_breakdown(db, order)
    db.commit()
    return order


def _inventory_qty(db: Session, product_id: int) -> int:
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == product_id)
        .first()
    )
    return int(item.quantity) if item else 0


# ---------------------------------------------------------------------------
# apply_status_change — audit + idempotency
# ---------------------------------------------------------------------------


def test_apply_status_change_writes_audit_row_on_real_transition(db):
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()

    changed = apply_status_change(
        db, order, new_status="cancelled", source_signal="ml_webhook",
    )
    db.commit()
    assert changed is True
    assert order.status == "CANCELLED"

    events = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == order.id)
        .order_by(SalesOrderStatusEvent.changed_at.asc())
        .all()
    )
    # First event = the initial-status record (NULL → PAID), second =
    # the transition (PAID → CANCELLED).
    assert [e.from_status for e in events] == [None, "PAID"]
    assert [e.to_status for e in events] == ["PAID", "CANCELLED"]
    assert events[-1].source_signal == "ml_webhook"


def test_apply_status_change_is_idempotent_when_status_matches(db):
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()

    # Re-applying the same status (or its lower-case form) is a no-op.
    changed = apply_status_change(
        db, order, new_status="PAID", source_signal="ml_poll",
    )
    assert changed is False
    changed = apply_status_change(
        db, order, new_status="paid", source_signal="ml_poll",
    )
    assert changed is False

    events = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == order.id)
        .count()
    )
    assert events == 1  # only the initial record


def test_record_initial_status_is_idempotent(db):
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    record_initial_status(db, order, source_signal="ml_webhook")  # racing
    db.commit()
    count = (
        db.query(SalesOrderStatusEvent)
        .filter(SalesOrderStatusEvent.order_id == order.id)
        .count()
    )
    assert count == 1


# ---------------------------------------------------------------------------
# reversed_at toggling
# ---------------------------------------------------------------------------


def test_reversed_at_set_when_leaving_realized_set(db):
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()
    assert order.cost_breakdown.reversed_at is None

    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()
    assert order.cost_breakdown.reversed_at is not None


def test_reversed_at_cleared_when_returning_to_realized(db):
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()
    assert order.cost_breakdown.reversed_at is not None

    # Operator-initiated un-cancel (or marketplace flipping the order
    # back). The breakdown must rejoin current-period rollups.
    apply_status_change(db, order, new_status="paid", source_signal="manual")
    db.commit()
    assert order.cost_breakdown.reversed_at is None


def test_reversed_breakdown_excluded_from_rollup(db):
    """End-to-end: a reversed order's revenue stops counting in the
    aggregate-rollup query so the dashboard's net-margin numbers
    don't lie."""
    order = _seed_order_with_inventory(db, status="PAID")
    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()

    rollup_before = order_cost_engine.aggregate_rollup(db, window_days=30)
    assert rollup_before["orders"] == 1
    assert rollup_before["revenue_amount_mxn"] > 0

    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    rollup_after = order_cost_engine.aggregate_rollup(db, window_days=30)
    assert rollup_after["orders"] == 0
    assert rollup_after["revenue_amount_mxn"] == 0.0


# ---------------------------------------------------------------------------
# Stock re-credit semantics
# ---------------------------------------------------------------------------


def test_recredit_fires_on_realized_to_cancelled_when_never_shipped(db):
    """Cancellation BEFORE shipment re-credits stock. The order's
    initial status is PAID with no SHIPPED event in the audit; the
    cancel transition therefore credits qty back."""
    order = _seed_order_with_inventory(db, status="PAID", qty=3)
    product_id = order.items[0].product_id
    starting_qty = _inventory_qty(db, product_id)

    record_initial_status(db, order, source_signal="ml_poll")
    db.commit()

    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    assert _inventory_qty(db, product_id) == starting_qty + 3
    assert order.stock_recredited_at is not None


def test_recredit_skipped_when_order_was_ever_shipped(db):
    """Cancellation AFTER shipment must NOT re-credit — product
    already left the warehouse. The audit tracks whether SHIPPED was
    ever seen."""
    order = _seed_order_with_inventory(db, status="PAID", qty=3)
    product_id = order.items[0].product_id
    starting_qty = _inventory_qty(db, product_id)

    record_initial_status(db, order, source_signal="ml_poll")
    apply_status_change(db, order, new_status="shipped", source_signal="ml_poll")
    db.commit()

    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    assert _inventory_qty(db, product_id) == starting_qty
    assert order.stock_recredited_at is None


def test_recredit_is_idempotent_on_repeated_cancellation(db):
    """Re-polling a cancelled order can't double-credit."""
    order = _seed_order_with_inventory(db, status="PAID", qty=3)
    product_id = order.items[0].product_id
    starting_qty = _inventory_qty(db, product_id)
    record_initial_status(db, order, source_signal="ml_poll")
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()
    after_first = _inventory_qty(db, product_id)
    assert after_first == starting_qty + 3

    # A second poll re-observes the same cancelled status. Audit row
    # already exists for this transition (so apply returns False),
    # and the order.stock_recredited_at is non-NULL — stock must
    # stay where it is.
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()
    assert _inventory_qty(db, product_id) == after_first


def test_recredit_skipped_when_transition_is_pending_to_cancelled(db):
    """Pending → cancelled is not a 'realized → cancelled' transition;
    the order never even reached a realized state so there was no
    stock decrement to reverse. Don't re-credit."""
    order = _seed_order_with_inventory(db, status="PENDING", qty=3)
    product_id = order.items[0].product_id
    starting_qty = _inventory_qty(db, product_id)

    record_initial_status(db, order, source_signal="ml_poll")
    apply_status_change(db, order, new_status="cancelled", source_signal="ml_poll")
    db.commit()

    assert _inventory_qty(db, product_id) == starting_qty
    assert order.stock_recredited_at is None
