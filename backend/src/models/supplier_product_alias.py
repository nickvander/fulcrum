"""
Learned supplier aliases for product matching.

These rows capture approved supplier-specific names/SKUs such as Alibaba line
item descriptions without overwriting the canonical supplier-product relation.
"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class SupplierProductAlias(Base):
    __tablename__ = "supplier_product_aliases"
    __table_args__ = (
        UniqueConstraint("supplier_id", "normalized_sku", name="uq_supplier_alias_sku"),
        UniqueConstraint("supplier_id", "normalized_name", name="uq_supplier_alias_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)

    alias_sku = Column(String, nullable=True)
    alias_name = Column(String, nullable=True)
    normalized_sku = Column(String, nullable=True, index=True)
    normalized_name = Column(String, nullable=True, index=True)

    source = Column(String, default="po_confirmation")
    confidence = Column(Float, default=1.0)
    match_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    last_matched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplier = relationship("Supplier")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    @property
    def product_name(self):
        return self.product.name if self.product else None

    @property
    def variant_name(self):
        return self.variant.name if self.variant else None
