from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.crud.crud_purchase_order import purchase_order as crud_purchase_order
from src.schemas.purchase_order import PurchaseOrderStatus

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

    def receive_items(self, db: Session, po_id: int, received_items: list):
        """
        Process receiving items for a Purchase Order.
        received_items: List of dicts { "product_id": int, "quantity_received": int }
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
            
            # Update Inventory
            inventory_service.adjust_stock(
                db=db,
                product_id=pid,
                adjustment=qty,
                reason=f"Received PO #{po.id}",
                user_id="system" # Or pass user from API
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

purchase_order_service = PurchaseOrderService()
