from sqlalchemy import Column, Integer, String, Float, ForeignKey, TIMESTAMP, Enum, DATE
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


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    status = Column(String, default="PENDING")
    order_date = Column(TIMESTAMP)
    expected_delivery_date = Column(DATE, nullable=True)

    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    cost_per_unit = Column(Float)

    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
