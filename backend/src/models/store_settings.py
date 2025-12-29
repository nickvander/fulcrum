from sqlalchemy import Column, Integer, JSON
from .base import Base

class StoreSettings(Base):
    __tablename__ = "store_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    # Using JSON for flexibility as requested for "Store Settings" generally
    settings = Column(JSON, default={})
    
    # Explicit columns for core features to ensure type safety
    low_inventory_days_default = Column(Integer, default=30)
    low_stock_quantity_default = Column(Integer, default=10)
