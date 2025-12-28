from typing import List
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
                    unit_cost=item_in.unit_cost
                )
                db.add(db_item)
                total_amount += (item_in.quantity_ordered * item_in.unit_cost)
        
        # Update total (simple logic, likely needs improvement later)
        db_obj.total_amount = total_amount
        db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

purchase_order = CRUDPurchaseOrder(PurchaseOrder)
