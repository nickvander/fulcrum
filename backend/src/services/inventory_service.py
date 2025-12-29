from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from src.models.inventory import InventoryItem, InventoryAdjustment

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

    def assemble_bundle(
        self,
        db: Session,
        bundle_id: int,
        quantity: int,
        user_id: Optional[str] = "system"
    ):
        """
        Assembles a bundle by decreasing component stock and increasing bundle stock.
        """
        from sqlalchemy.orm import joinedload
        from src.models.product import Product 

        bundle = db.query(Product).options(joinedload(Product.bundle_components)).filter(Product.id == bundle_id).first()
        if not bundle or not bundle.is_bundle:
             raise ValueError("Product is not a bundle")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if not bundle.bundle_components:
             raise ValueError("Bundle has no components")

        # Verify stock sufficiency first (atomic-ish check)
        for comp in bundle.bundle_components:
            required = comp.quantity * quantity
            stock = db.query(InventoryItem).filter(
                InventoryItem.product_id == comp.component_id,
                InventoryItem.location == "default"
            ).first()
            current = stock.quantity if stock else 0
            if current < required:
                comp_name = comp.component.name if comp.component else f"ID {comp.component_id}"
                raise ValueError(f"Insufficient stock for {comp_name}. Required: {required}, Available: {current}")

        # Execute deductions
        for comp in bundle.bundle_components:
            self.adjust_stock(
                db, 
                comp.component_id, 
                -(comp.quantity * quantity), 
                reason=f"Used for Bundle {bundle.sku or bundle.id}", 
                user_id=user_id
            )

        # Add bundle stock
        self.adjust_stock(
            db, 
            bundle_id, 
            quantity, 
            reason="Bundle Assembly", 
            user_id=user_id
        )

inventory_service = InventoryService()
