"""
Model for the SupplierProduct join table.
Allows products to have multiple suppliers with different prices/SKUs.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class SupplierProduct(Base):
    """
    Join table linking products to suppliers.
    Allows tracking different SKUs and prices from multiple vendors.
    """
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    
    # Supplier-specific product info
    supplier_sku = Column(String, nullable=True, index=True)  # Supplier's product code
    supplier_product_name = Column(String, nullable=True)     # Literal name used by supplier
    cost_price = Column(Float, default=0.0)  # Price from this supplier
    
    # Relationship metadata
    is_primary = Column(Boolean, default=False)  # Primary supplier for this product
    lead_time_days = Column(Integer, nullable=True)  # Expected delivery time
    minimum_order_qty = Column(Float, default=1.0)  # Minimum order quantity
    notes = Column(String, nullable=True)  # Supplier-specific notes
    
    # Tracking
    last_ordered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", backref="supplier_products")
    supplier = relationship("Supplier", backref="supplier_products")

    @property
    def product_name(self):
        return self.product.name if self.product else None

    @property
    def supplier_name(self):
        return self.supplier.name if self.supplier else None
