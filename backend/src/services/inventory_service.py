from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from src.models.inventory import InventoryItem, InventoryAdjustment
from src.schemas.inventory import StockAdjustment

class InventoryService:
    def adjust_stock(
        self,
        db: Session,
        product_id: int,
        adjustment: int,
        reason: Optional[str] = None,
        location: str = "default",
        user_id: Optional[str] = "system"
    ) -> InventoryItem:
        """
        Adjust stock for a product at a specific location.
        Creates an audit trail (InventoryAdjustment) and updates/creates the InventoryItem.
        """
        
        # 1. Create audit log
        inventory_adjustment = InventoryAdjustment(
            product_id=product_id,
            adjustment=adjustment,
            reason=reason,
            timestamp=datetime.utcnow(),
            created_by=str(user_id)
        )
        db.add(inventory_adjustment)
        
        # 2. Get existing stock record
        existing_inventory = db.query(InventoryItem).filter(
            InventoryItem.product_id == product_id,
            InventoryItem.location == location
        ).first()

        current_qty = existing_inventory.quantity if existing_inventory else 0
        new_qty = current_qty + adjustment

        # 3. Update or Create InventoryItem
        if existing_inventory:
            existing_inventory.quantity = new_qty
            final_item = existing_inventory
        else:
            final_item = InventoryItem(
                product_id=product_id,
                quantity=new_qty,
                location=location
            )
            db.add(final_item)
            
        return final_item

inventory_service = InventoryService()
