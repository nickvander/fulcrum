from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class ProductInventorySettings(Base):
    __tablename__ = "product_inventory_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    low_inventory_days_threshold = Column(Integer, nullable=True) # Null means use global default
    low_stock_quantity_threshold = Column(Integer, nullable=True) # Null means use global default
