from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    sku = Column(String, unique=True, index=True)
    supplier_sku = Column(String, nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    default_resale_price = Column(Float)
    cost_price = Column(Float) # Last Purchase Price
    average_cost = Column(Float, default=0.0) # Weighted Average Cost
    properties = Column(String)  # Simple JSON as string for now
    embedding = Column(Vector(384)) # Example dimension
    manufacturer = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    category = Column(String, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    is_bundle = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplier = relationship("Supplier")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="product", cascade="all, delete-orphan")
    inventory_adjustments = relationship("InventoryAdjustment", back_populates="product", cascade="all, delete-orphan")
    custom_fields = relationship("ProductCustomField", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    marketplace_listings = relationship("MarketplaceListing", back_populates="product", cascade="all, delete-orphan")

    @property
    def primary_image(self):
        if not self.images:
            return None
        return next((img for img in self.images if img.is_primary), self.images[0])
    
    @property
    def image_url(self):
        """Returns the primary image URL for use in marketing schemas."""
        if self.primary_image:
            return self.primary_image.image_path
        return None
    
    # Bundle relationship
    bundle_components = relationship(
        "BundleComponent", 
        foreign_keys="BundleComponent.bundle_id", 
        back_populates="bundle", 
        cascade="all, delete-orphan"
    )
    part_of_bundles = relationship(
        "BundleComponent",
        foreign_keys="BundleComponent.component_id",
        back_populates="component"
    )

class BundleComponent(Base):
    __tablename__ = "bundle_components"

    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    component_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    quantity = Column(Integer, default=1)

    bundle = relationship("Product", foreign_keys=[bundle_id], back_populates="bundle_components")
    component = relationship("Product", foreign_keys=[component_id], back_populates="part_of_bundles")

    @property
    def bundle_name(self):
        return self.bundle.name if self.bundle else None

    @property
    def bundle_image(self):
        if self.bundle and self.bundle.primary_image:
            return self.bundle.primary_image.image_path
        return None

    @property
    def component_name(self):
        return self.component.name if self.component else None

    @property
    def component_image(self):
        if self.component and self.component.primary_image:
            return self.component.primary_image.image_path
        return None

    @property
    def bundle_stock(self):
        if self.bundle and self.bundle.inventory_items:
            return sum(item.quantity for item in self.bundle.inventory_items)
        return 0

    @property
    def component_stock(self):
        if self.component and self.component.inventory_items:
            return sum(item.quantity for item in self.component.inventory_items)
        return 0

    @property
    def component_cost(self):
        return self.component.cost_price if self.component else 0.0

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    image_path = Column(String)
    is_primary = Column(Integer, default=0) # 0 for false, 1 for true
    source = Column(String)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)

    product = relationship("Product", back_populates="images")
