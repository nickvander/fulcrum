from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.inventory import InventoryItem, InventoryAdjustment
from src.models.order import SalesOrder, SalesOrderItem

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

    def calculate_sales_velocity(self, db: Session, product_id: int, days: int = 30) -> float:
        """
        Calculates average daily sales over the last N days.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Query sum of quantity for this product in completed/shipped orders
        # We include COMPLETED, SHIPPED. If statuses differ, adjust here.
        total_sold = db.query(func.sum(SalesOrderItem.quantity)).join(SalesOrder).filter(
            SalesOrderItem.product_id == product_id,
            SalesOrder.created_at >= cutoff_date,
            SalesOrder.status.in_(["COMPLETED", "SHIPPED"]) 
        ).scalar() or 0
        
        return float(total_sold) / float(days)

    def calculate_days_of_inventory(self, db: Session, product_id: int) -> float:
        """
        Calculates estimated days of stock remaining based on sales velocity.
        Returns 999.0 if velocity is 0 (infinite stock relative to sales).
        """
        # Get current stock (sum across all locations)
        stock = db.query(func.sum(InventoryItem.quantity)).filter(
            InventoryItem.product_id == product_id
        ).scalar() or 0
        
        velocity = self.calculate_sales_velocity(db, product_id)
        
        if velocity <= 0:
            return 999.0 
            
        return float(stock) / velocity

    def get_effective_low_inventory_threshold(self, db: Session, product_id: int) -> int:
        """
        Returns the low inventory threshold (days) for a product.
        Checks product specific override first, then falls back to global store setting.
        """
        from src.crud.crud_product_inventory_settings import product_inventory_settings as crud_pis
        from src.crud.crud_store_settings import store_settings as crud_ss
        
        # 1. Check Product Specific
        prod_settings = crud_pis.get_by_product(db, product_id=product_id)
        if prod_settings and prod_settings.low_inventory_days_threshold is not None:
             return prod_settings.low_inventory_days_threshold
             
        # 2. Check Global
        store_settings = crud_ss.get_settings(db)
        return store_settings.low_inventory_days_default

    def get_effective_low_stock_quantity_threshold(self, db: Session, product_id: int) -> int:
        """
        Returns the low stock quantity threshold for a product.
        Checks product specific override first, then falls back to global store setting.
        """
        from src.crud.crud_product_inventory_settings import product_inventory_settings as crud_pis
        from src.crud.crud_store_settings import store_settings as crud_ss
        
        # 1. Check Product Specific
        prod_settings = crud_pis.get_by_product(db, product_id=product_id)
        if prod_settings and prod_settings.low_stock_quantity_threshold is not None:
             return prod_settings.low_stock_quantity_threshold
             
        # 2. Check Global
        store_settings = crud_ss.get_settings(db)
        return store_settings.low_stock_quantity_default

    def get_total_stock_quantity(self, db: Session, product_id: int) -> int:
        from src.models.inventory import InventoryItem
        total_quantity = db.query(func.sum(InventoryItem.quantity)).filter(InventoryItem.product_id == product_id).scalar()
        return total_quantity or 0

inventory_service = InventoryService()
