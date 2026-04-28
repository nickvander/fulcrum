from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    
    quantity_ordered = Column(Float, default=0.0)
    quantity_received = Column(Float, default=0.0)
    
    # Cost breakdown for transparency
    base_cost = Column(Float, default=0.0)  # Original supplier price per unit
    shipping_allocated = Column(Float, default=0.0)  # Freight/delivery per unit
    taxes_allocated = Column(Float, default=0.0)  # Import duties/customs per unit
    other_allocated = Column(Float, default=0.0)  # Insurance, handling, etc. per unit
    costs_applied_at = Column(DateTime(timezone=True), nullable=True)  # When costs were allocated
    
    # Total unit cost (base + all allocations)
    unit_cost = Column(Float, default=0.0)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

