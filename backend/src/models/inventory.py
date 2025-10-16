from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    quantity = Column(Integer)
    location = Column(String)

    product = relationship("Product", back_populates="inventory_items")


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    adjustment = Column(Integer)  # Positive for increases, negative for decreases
    reason = Column(String)  # Reason for the adjustment
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)  # User who made the adjustment

    product = relationship("Product", back_populates="inventory_adjustments")
