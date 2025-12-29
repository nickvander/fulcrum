from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.purchase_order import PurchaseOrder
from src.models.purchase_order_item import PurchaseOrderItem
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderUpdate

class CRUDPurchaseOrder(CRUDBase[PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate]):
    def create_with_items(self, db: Session, *, obj_in: PurchaseOrderCreate) -> PurchaseOrder:
        # Separate items from PO data
        items_data = obj_in.items
        po_data = obj_in.model_dump(exclude={"items"})
        
        # Create PO
        db_obj = PurchaseOrder(**po_data)
        db.add(db_obj)
        db.flush() # Get ID
        
        # Create Items
        total_amount = 0.0
        if items_data:
            for item_in in items_data:
                db_item = PurchaseOrderItem(
                    po_id=db_obj.id,
                    product_id=item_in.product_id,
                    quantity_ordered=item_in.quantity_ordered,
                    unit_cost=item_in.unit_cost,
                    base_cost=item_in.unit_cost # Initialize base cost
                )
                db.add(db_item)
                total_amount += (item_in.quantity_ordered * item_in.unit_cost)
        
        # Update total (simple logic, likely needs improvement later)
        db_obj.total_amount = total_amount
        db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: PurchaseOrder, obj_in: PurchaseOrderUpdate | dict) -> PurchaseOrder:
        # Check if obj_in contains items
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        items_data = update_data.pop("items", None)
        
        # Standard update for valid fields
        db_obj = super().update(db, db_obj=db_obj, obj_in=update_data)
        
        # If items are provided, sync them
        if items_data is not None:
            # For simplicity: Delete existing items that are not in the new list (if we tracked IDs),
            # OR just delete all and recreate (easiest for now, but loses received counts if any).
            # Since editing is usually restricted if items received, valid to replace for now.
            # Ideally, we should diff.
            
            # Simple Replace Strategy (Safe for Draft/Ordered before receiving):
            # 1. Delete all existing items
            db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == db_obj.id).delete()
            
            # 2. Add new items
            total_amount = 0.0
            for item in items_data:
                # Handle dict or object
                i_prod_id = item.get("product_id") if isinstance(item, dict) else item.product_id
                i_qty = item.get("quantity_ordered") if isinstance(item, dict) else item.quantity_ordered
                i_cost = item.get("unit_cost") if isinstance(item, dict) else item.unit_cost
                
                db_item = PurchaseOrderItem(
                    po_id=db_obj.id,
                    product_id=i_prod_id,
                    quantity_ordered=i_qty,
                    unit_cost=i_cost,
                    base_cost=i_cost # Initialize base cost
                )
                db.add(db_item)
                total_amount += (i_qty * i_cost)
            
            db_obj.total_amount = total_amount
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
        return db_obj

purchase_order = CRUDPurchaseOrder(PurchaseOrder)
