from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)  # Allow null for non-variant inventory
    quantity = Column(Integer, default=0)
    location = Column(String, default="default")  # Warehouse location, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    variant = relationship("ProductVariant", back_populates="inventory_items")


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)  # Nullable to support variants
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)  # Nullable to support base products
    adjustment = Column(Integer, nullable=False)  # Positive for additions, negative for subtractions
    reason = Column(String)  # Reason for the adjustment
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=True)  # Timestamp of the adjustment
    created_by = Column(String, nullable=False)  # User who made the adjustment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_adjustments")
    variant = relationship("ProductVariant", back_populates="inventory_adjustments")
