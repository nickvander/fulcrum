from sqlalchemy import Column, Integer, String, Float, ForeignKey, TIMESTAMP, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base

class OrderSource(enum.Enum):
    FULCRUM = "FULCRUM"
    MERCADOLIBRE = "MERCADOLIBRE"
    AMAZON = "AMAZON"

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    # client_id = Column(Integer, ForeignKey("clients.id")) # Assuming a clients table
    status = Column(String)
    total_price = Column(Float)
    created_at = Column(TIMESTAMP)
    source = Column(Enum(OrderSource))
    external_order_id = Column(String)

    items = relationship("SalesOrderItem", back_populates="order")

class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_per_unit = Column(Float)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")
