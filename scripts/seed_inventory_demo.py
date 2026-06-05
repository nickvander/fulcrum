"""One-off demo seed for the inventory-ops features shipped this cycle.
Drives the REAL service write paths so adjustment `source`s get stamped
authentically. Idempotent-ish: safe to re-run (it just adds more rows).

Run inside the backend container:
    cat scripts/seed_inventory_demo.py | docker compose exec -T backend python
"""
from src.database import SessionLocal
from src.services.inventory_service import inventory_service
from src.services.stock_transfer_service import stock_transfer_service
from src.services import inventory_count_service
from src.models.stock_transfer import StockTransfer, StockTransferItem, StockTransferStatus
from src.models.inventory import InventoryAdjustmentReasonCode

db = SessionLocal()


def log(msg):
    print(f"[inv-demo] {msg}")


# 1. Opening stock at 'default' for products 1..12 (some low / zero so the
#    stock pills show healthy / low / out states).
stock_levels = {1: 120, 2: 60, 3: 8, 4: 0, 5: 200, 6: 35, 7: 90, 8: 15, 9: 50, 10: 75, 11: 5, 12: 140}
for pid, qty in stock_levels.items():
    if qty > 0:
        inventory_service.adjust_stock(
            db, product_id=pid, adjustment=qty, location="default",
            reason="Opening stock (demo seed)",
            reason_code=InventoryAdjustmentReasonCode.MANUAL,
        )
db.commit()
log(f"opening stock set on {len(stock_levels)} products")


def new_draft(pid, planned):
    t = StockTransfer(source_location="default", dest_location="ml-full", status="draft")
    db.add(t)
    db.flush()
    db.add(StockTransferItem(transfer_id=t.id, product_id=pid, qty_planned=planned))
    db.commit()
    return t


# 2a. Shipped, not yet received → product list "+N en camino" (+30 on product 1).
try:
    tA = new_draft(1, 30)
    stock_transfer_service.ship(db, transfer_id=tA.id)
    db.commit()
    log(f"transfer #{tA.id}: shipped 30 of product 1 (in-transit)")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"transfer A failed: {e}")

# 2b. Shipped then partially received (12 of 20) → "+8 en camino" on product 5;
#     shows on reconciliation but NOT flagged (in-transit shortfall).
try:
    tB = new_draft(5, 20)
    stock_transfer_service.ship(db, transfer_id=tB.id)
    stock_transfer_service.receive_items(db, transfer_id=tB.id, received_items=[{"product_id": 5, "quantity": 12}])
    db.commit()
    log(f"transfer #{tB.id}: partially received 12/20 of product 5")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"transfer B failed: {e}")

# 2c. SETTLED shortfall (received, shipped 15 but only 11 landed) →
#     reconciliation "Discrepancia -4" flagged. Built directly so it lands in
#     the terminal RECEIVED state with a gap.
try:
    tC = StockTransfer(source_location="default", dest_location="ml-full",
                       status=StockTransferStatus.RECEIVED.value)
    db.add(tC)
    db.flush()
    db.add(StockTransferItem(transfer_id=tC.id, product_id=7, qty_planned=15, qty_shipped=15, qty_received=11))
    db.commit()
    log(f"transfer #{tC.id}: received with shortfall 11/15 of product 7 (discrepancy)")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"transfer C failed: {e}")

# 2d. Over-receipt (received 13, shipped 10) → reconciliation "Discrepancia +3" flagged.
try:
    tD = StockTransfer(source_location="default", dest_location="ml-full",
                       status=StockTransferStatus.PARTIALLY_RECEIVED.value)
    db.add(tD)
    db.flush()
    db.add(StockTransferItem(transfer_id=tD.id, product_id=9, qty_planned=10, qty_shipped=10, qty_received=13))
    db.commit()
    log(f"transfer #{tD.id}: over-receipt 13/10 of product 9 (discrepancy)")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"transfer D failed: {e}")

# 3. A committed physical count → inventory_count-sourced adjustment in the audit.
try:
    sku = db.execute(__import__("sqlalchemy").text("SELECT sku FROM products WHERE id = 2")).scalar()
    session = inventory_count_service.start_session(db, actor=None, location="default")
    item = inventory_count_service.add_item_by_sku(db, session=session, sku=sku)
    inventory_count_service.update_count(db, session=session, item_id=item.id, counted_quantity=54)
    inventory_count_service.commit_session(db, session=session, actor=None)
    db.commit()
    log(f"count session #{session.id}: counted {sku} 54 vs expected 60 (recount -6)")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"count session failed: {e}")

# 4. A manual shrinkage adjustment → a "No source" row in the audit.
try:
    inventory_service.adjust_stock(
        db, product_id=3, adjustment=-2, location="default",
        reason="Damaged in handling", reason_code=InventoryAdjustmentReasonCode.DAMAGE,
    )
    db.commit()
    log("manual damage adjustment on product 3 (-2)")
except Exception as e:  # noqa: BLE001
    db.rollback()
    log(f"manual adjustment failed: {e}")

log("done.")
