from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Red - Large", "Blue - Medium"
    sku = Column(String, unique=True, index=True)  # Unique SKU for this variant
    description = Column(String)
    price = Column(Float)  # Override default price
    cost_price = Column(Float)  # Override default cost price
    attributes = Column(String)  # JSON string to store variant attributes like size, color, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to main product
    product = relationship("Product", back_populates="variants")
    # Relationship to inventory items
    inventory_items = relationship("InventoryItem", back_populates="variant", cascade="all, delete-orphan")
    inventory_adjustments = relationship("InventoryAdjustment", back_populates="variant", cascade="all, delete-orphan")
