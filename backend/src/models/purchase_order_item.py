from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity_ordered = Column(Float, default=0.0)
    quantity_received = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0) # Cost at time of order

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
