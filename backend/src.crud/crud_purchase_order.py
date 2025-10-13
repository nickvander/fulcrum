from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.order import PurchaseOrder, PurchaseOrderItem
from src.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderUpdate

class CRUDPurchaseOrder(CRUDBase[PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate]):

    def create(self, db: Session, *, obj_in: PurchaseOrderCreate) -> PurchaseOrder:
        # Create the PurchaseOrder object
        db_obj = PurchaseOrder(
            supplier_id=obj_in.supplier_id,
            status=obj_in.status,
            order_date=obj_in.order_date,
            expected_delivery_date=obj_in.expected_delivery_date,
        )
        db.add(db_obj)
        db.flush() # Use flush to get the ID of the new purchase order

        # Create the PurchaseOrderItem objects
        for item_in in obj_in.items:
            db_item = PurchaseOrderItem(
                purchase_order_id=db_obj.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                cost_per_unit=item_in.cost_per_unit,
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_obj)
        return db_obj

purchase_order = CRUDPurchaseOrder(PurchaseOrder)
