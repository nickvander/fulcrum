from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.crud.crud_product import product as crud_product
from src.schemas.purchase_order import PurchaseOrderStatus
from src.models.inventory import InventoryItem
from sqlalchemy.sql import func

class PurchaseOrderService:
    def transition_status(self, db: Session, po_id: int, new_status: PurchaseOrderStatus):
        po = crud_purchase_order.get(db=db, id=po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")

        current_status = po.status
        
        # Basic state machine validation
        # Only allow Draft -> Ordered -> Partially Received -> Completed -> Closed
        # (Simplified logic for now, can be expanded)
        
        # Allow returning to Draft from Ordered? Maybe.
        
        if current_status == PurchaseOrderStatus.CLOSED and new_status != PurchaseOrderStatus.CLOSED:
             raise HTTPException(status_code=400, detail="Cannot reopen a closed Purchase Order")

        # Update status
        updated_po = crud_purchase_order.update(db=db, db_obj=po, obj_in={"status": new_status})
        return updated_po

    def receive_items(self, db: Session, po_id: int, received_items: list, user=None):
        """
        Process receiving items for a Purchase Order.
        received_items: List of dicts { "product_id": int, "quantity_received": int }
        user: Current user object (optional)
        """
        from src.services.inventory_service import inventory_service
        
        po = crud_purchase_order.get(db=db, id=po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")
        
        if po.status == PurchaseOrderStatus.DRAFT:
             raise HTTPException(status_code=400, detail="Cannot receive items for a Draft PO")
        
        if po.status == PurchaseOrderStatus.CLOSED:
             raise HTTPException(status_code=400, detail="Cannot receive items for a Closed PO")

        updated_items_count = 0

        # Map current items for easy lookup
        po_items_map = {item.product_id: item for item in po.items}

        for receive_data in received_items:
            pid = receive_data.get("product_id") or receive_data.product_id
            qty = receive_data.get("quantity") or receive_data.quantity
            
            if not pid or not qty:
                continue

            item = po_items_map.get(pid)
            if not item:
                # Warning: Item not in PO? For now, skip or error.
                # Strictly only allow receiving items that are on the PO.
                continue
            
            # Update PO Item
            # Ideally validation checks delta vs ordered, but allow over-receiving for flexibility
            item.quantity_received = (item.quantity_received or 0) + qty
            db.add(item)

            # --- Cost Update Logic (Dual Pricing) ---
            # Fetch product explicitly to ensure session tracking
            product = crud_product.get(db=db, id=pid)
            if product:
                current_qty_log = sum(inv.quantity for inv in product.inventory_items) if product.inventory_items else 0
                print(f"[PO Receive] Product {pid}: Current Stock {current_qty_log}, Old Avg {product.average_cost}, New Unit Cost {item.unit_cost}")

                # Explicitly query current total stock (before this receipt is processed by inventory service)
                current_stock_qty = db.query(func.sum(InventoryItem.quantity)).filter(InventoryItem.product_id == pid).scalar() or 0
                
                print(f"[PO Receive] Product {pid}: Db Stock {current_stock_qty}, Old Avg {product.average_cost}, New Unit Cost {item.unit_cost}")

                # 1. Capture old cost for fallback
                old_cost_price = product.cost_price

                # 2. Update Cost Price (Last Purchase Price)
                product.cost_price = item.unit_cost
                
                # 3. Weighted Average Cost
                current_avg_cost = product.average_cost or 0.0
                
                # If avg cost is missing but we have stock, try to estimate from old cost
                if current_avg_cost == 0 and current_stock_qty > 0 and old_cost_price:
                     current_avg_cost = old_cost_price

                total_existing_value = current_stock_qty * current_avg_cost
                new_received_value = qty * item.unit_cost
                
                total_new_qty = current_stock_qty + qty
                
                if total_new_qty > 0:
                    new_average_cost = (total_existing_value + new_received_value) / total_new_qty
                    product.average_cost = round(new_average_cost, 4)
                
                db.add(product)
            # ----------------------------------------
            
            # Update Inventory
            inventory_service.adjust_stock(
                db=db,
                product_id=pid,
                adjustment=qty,
                reason=f"Received PO #{po.id}",

                user_id=user.email if user else "system" 
            )
            updated_items_count += 1
        
        db.commit()
        db.refresh(po)

        # Check PO Status
        # Calculate if all items are fully received
        all_fully_received = True
        has_some_receipts = False

        for item in po.items:
            received = item.quantity_received or 0
            ordered = item.quantity_ordered
            if received > 0:
                has_some_receipts = True
            
            if received < ordered:
                all_fully_received = False
        
        new_status = po.status
        if all_fully_received:
            new_status = PurchaseOrderStatus.COMPLETED
        elif has_some_receipts:
            new_status = PurchaseOrderStatus.PARTIALLY_RECEIVED
            
        if new_status != po.status:
             crud_purchase_order.update(db=db, db_obj=po, obj_in={"status": new_status})
        
        return po

    def calculate_landed_costs(self, db: Session, po_id: int):
        """
        Distribute PO-level shipping, tax, and other costs across individual items
        based on their contribution to the total value.
        """
        po = crud_purchase_order.get(db=db, id=po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase Order not found")
        
        # Calculate total subtotal (quantity ordered * base cost)
        subtotal = sum(item.quantity_ordered * item.base_cost for item in po.items)
        if subtotal == 0:
            return po
        
        total_shipping = po.shipping_cost or 0.0
        total_tax = po.tax_amount or 0.0
        total_other = po.other_costs or 0.0
        
        for item in po.items:
            item_share = (item.quantity_ordered * item.base_cost) / subtotal
            
            # Allocation per unit
            item.shipping_allocated = (total_shipping * item_share) / item.quantity_ordered if item.quantity_ordered > 0 else 0
            item.taxes_allocated = (total_tax * item_share) / item.quantity_ordered if item.quantity_ordered > 0 else 0
            item.other_allocated = (total_other * item_share) / item.quantity_ordered if item.quantity_ordered > 0 else 0
            
            # Update total unit cost
            item.unit_cost = item.base_cost + item.shipping_allocated + item.taxes_allocated + item.other_allocated
            item.costs_applied_at = func.now()
            
            db.add(item)
        
        db.commit()
        db.refresh(po)
        return po

purchase_order_service = PurchaseOrderService()
