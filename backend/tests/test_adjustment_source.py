"""P2-8 — structured `source` / `source_id` stamping across every
inventory-adjustment write path.

P1-9 added the columns + the PO-receiving write path; this verifies the
remaining write paths stamp the right origin so the unified stock-history
timeline can linkify each movement without parsing the localized reason.
"""
import pytest
from sqlalchemy.orm import Session

from src.models.inventory import (
    InventoryAdjustment,
    InventoryAdjustmentReasonCode,
    InventoryAdjustmentSource,
)
from src.models.product import Product
from src.services.inventory_service import inventory_service

pytestmark = pytest.mark.db


def _latest_adjustment(db: Session, product_id: int, adjustment: int) -> InventoryAdjustment:
    return (
        db.query(InventoryAdjustment)
        .filter(
            InventoryAdjustment.product_id == product_id,
            InventoryAdjustment.adjustment == adjustment,
        )
        .order_by(InventoryAdjustment.id.desc())
        .first()
    )


def test_adjust_stock_persists_source(db: Session, test_product: Product):
    inventory_service.adjust_stock(
        db,
        product_id=test_product.id,
        adjustment=7,
        reason="x",
        source=InventoryAdjustmentSource.STOCK_TRANSFER,
        source_id=42,
    )
    db.commit()
    adj = _latest_adjustment(db, test_product.id, 7)
    assert adj.source == "stock_transfer"
    assert adj.source_id == 42


def test_decrement_stock_atomic_persists_source(db: Session, test_product: Product):
    inventory_service.adjust_stock(db, product_id=test_product.id, adjustment=10)
    db.commit()
    inventory_service.decrement_stock_atomic(
        db,
        product_id=test_product.id,
        quantity=3,
        reason_code=InventoryAdjustmentReasonCode.SALE,
        source=InventoryAdjustmentSource.SALES_ORDER,
        source_id=99,
    )
    db.commit()
    adj = _latest_adjustment(db, test_product.id, -3)
    assert adj.source == "sales_order"
    assert adj.source_id == 99


def test_reversal_links_to_original_adjustment(db: Session, test_product: Product):
    _item, original = inventory_service.record_adjustment(
        db,
        product_id=test_product.id,
        adjustment=5,
        reason="manual count fix",
        reason_code=InventoryAdjustmentReasonCode.MANUAL,
    )
    db.commit()

    reversal = inventory_service.reverse_adjustment(db, original.id, actor="tester")
    db.commit()

    assert reversal.source == InventoryAdjustmentSource.ADJUSTMENT_REVERSAL.value
    assert reversal.source_id == original.id
    assert reversal.reverses_adjustment_id == original.id


def test_bundle_assembly_stamps_both_legs(db: Session):
    from src.crud import crud_product
    from src.schemas.product import ProductCreate
    from src.models.product import BundleComponent

    comp = crud_product.product.create(
        db,
        obj_in=ProductCreate(name="Comp", sku="SRC-COMP", default_resale_price=10, cost_price=5),
    )
    inventory_service.adjust_stock(db, comp.id, 100, location="default")
    bundle = crud_product.product.create(
        db,
        obj_in=ProductCreate(name="Bndl", sku="SRC-BNDL", default_resale_price=30, cost_price=15, is_bundle=True),
    )
    db.add(BundleComponent(bundle_id=bundle.id, component_id=comp.id, quantity=2))
    db.commit()
    db.refresh(bundle)

    inventory_service.assemble_bundle(db, bundle_id=bundle.id, quantity=4)
    db.commit()

    # Component leg: -8 units, bundle leg: +4 units — both link to the bundle.
    comp_leg = _latest_adjustment(db, comp.id, -8)
    bundle_leg = _latest_adjustment(db, bundle.id, 4)
    assert comp_leg.source == "bundle_assembly"
    assert comp_leg.source_id == bundle.id
    assert bundle_leg.source == "bundle_assembly"
    assert bundle_leg.source_id == bundle.id


def test_count_commit_links_to_session(db: Session, test_product: Product):
    from src.services import inventory_count_service

    inventory_service.adjust_stock(db, test_product.id, 20, location="default")
    db.commit()

    session = inventory_count_service.start_session(db, actor=None, location="default")
    item = inventory_count_service.add_item_by_sku(db, session=session, sku=test_product.sku)
    inventory_count_service.update_count(
        db, session=session, item_id=item.id, counted_quantity=15
    )  # delta -5
    db.commit()

    inventory_count_service.commit_session(db, session=session, actor=None)
    db.commit()

    adj = _latest_adjustment(db, test_product.id, -5)
    assert adj.source == "inventory_count"
    assert adj.source_id == session.id


def test_transfer_ship_links_to_transfer(db: Session, test_product: Product):
    from src.models.stock_transfer import StockTransfer, StockTransferItem
    from src.services.stock_transfer_service import stock_transfer_service

    inventory_service.adjust_stock(db, test_product.id, 50, location="default")
    transfer = StockTransfer(source_location="default", dest_location="ml-full", status="draft")
    db.add(transfer)
    db.flush()
    db.add(
        StockTransferItem(transfer_id=transfer.id, product_id=test_product.id, qty_planned=8)
    )
    db.commit()

    stock_transfer_service.ship(db, transfer_id=transfer.id)
    db.commit()

    # Ship debits the source location by qty_planned.
    adj = _latest_adjustment(db, test_product.id, -8)
    assert adj.source == "stock_transfer"
    assert adj.source_id == transfer.id
