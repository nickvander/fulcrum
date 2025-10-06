from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    sku = Column(String, unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    default_resale_price = Column(Float)
    cost_price = Column(Float)
    properties = Column(String)  # Simple JSON as string for now
    embedding = Column(Vector(384)) # Example dimension

    supplier = relationship("Supplier")
    images = relationship("ProductImage", back_populates="product")
    inventory_items = relationship("InventoryItem", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_path = Column(String)
    is_primary = Column(Integer, default=0) # 0 for false, 1 for true
    source = Column(String)

    product = relationship("Product", back_populates="images")
