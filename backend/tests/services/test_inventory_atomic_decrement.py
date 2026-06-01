"""FP-03 — atomic, guarded stock decrement.

These tests pin the no-oversell / no-negative invariant of
``InventoryService.decrement_stock_atomic``: the conditional
``UPDATE ... WHERE quantity >= :n`` must reject any decrement that would
take stock below zero, leave existing stock untouched on rejection, and
write a ``-quantity`` audit row on success.
"""
import pytest

from src.models.inventory import (
    InventoryAdjustment,
    InventoryAdjustmentReasonCode,
    InventoryItem,
)
from src.models.product import Product
from src.services.inventory_service import (
    InsufficientStockError,
    InventoryService,
)

service = InventoryService()


def _seed_stock(db, product, qty, *, location="default", variant_id=None):
    db.add(
        InventoryItem(
            product_id=product.id,
            variant_id=variant_id,
            quantity=qty,
            location=location,
        )
    )
    db.commit()


@pytest.mark.db
def test_decrement_happy_path(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    item = service.decrement_stock_atomic(db, product_id=test_product.id, quantity=3)
    db.commit()
    assert item.quantity == 2


@pytest.mark.db
def test_decrement_exactly_to_zero(db, test_product: Product):
    _seed_stock(db, test_product, 1)
    item = service.decrement_stock_atomic(db, product_id=test_product.id, quantity=1)
    db.commit()
    assert item.quantity == 0


@pytest.mark.db
def test_decrement_rejects_oversell_and_leaves_stock_untouched(db, test_product: Product):
    """The core race guard: asking for more than on-hand is rejected and
    the existing quantity is NOT mutated (no oversell, no negative)."""
    _seed_stock(db, test_product, 1)
    with pytest.raises(InsufficientStockError):
        service.decrement_stock_atomic(db, product_id=test_product.id, quantity=2)
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.product_id == test_product.id)
        .one()
    )
    assert item.quantity == 1  # untouched — never went negative


@pytest.mark.db
def test_decrement_at_zero_is_rejected(db, test_product: Product):
    _seed_stock(db, test_product, 1)
    service.decrement_stock_atomic(db, product_id=test_product.id, quantity=1)
    db.commit()
    with pytest.raises(InsufficientStockError):
        service.decrement_stock_atomic(db, product_id=test_product.id, quantity=1)


@pytest.mark.db
def test_decrement_with_no_inventory_row_is_rejected(db, test_product: Product):
    with pytest.raises(InsufficientStockError):
        service.decrement_stock_atomic(db, product_id=test_product.id, quantity=1)


@pytest.mark.db
def test_decrement_writes_sale_audit_row(db, test_product: Product):
    _seed_stock(db, test_product, 4)
    service.decrement_stock_atomic(
        db, product_id=test_product.id, quantity=2, reason="online sale"
    )
    db.commit()
    adj = (
        db.query(InventoryAdjustment)
        .filter(InventoryAdjustment.product_id == test_product.id)
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )
    assert adj is not None
    assert adj.adjustment == -2
    assert adj.reason_code == InventoryAdjustmentReasonCode.SALE.value


@pytest.mark.db
def test_decrement_rejects_non_positive_quantity(db, test_product: Product):
    _seed_stock(db, test_product, 5)
    for bad in (0, -1):
        with pytest.raises(ValueError):
            service.decrement_stock_atomic(db, product_id=test_product.id, quantity=bad)
