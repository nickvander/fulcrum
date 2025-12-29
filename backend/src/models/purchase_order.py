from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base

class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    COMPLETED = "completed"
    CLOSED = "closed"

class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    status = Column(String, default=PurchaseOrderStatus.DRAFT.value) # Storing as string for simplicity/compatibility
    
    total_amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    exchange_rate = Column(Float, default=1.0)
    
    landed_cost = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    other_costs = Column(Float, default=0.0)

    # Payment Information
    payment_status = Column(String, default=PaymentStatus.UNPAID.value)
    payment_method = Column(String, nullable=True)
    custom_payer_name = Column(String, nullable=True)
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    notes = Column(String, nullable=True)

    ordered_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplier = relationship("Supplier", backref="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    invoices = relationship("SupplierInvoice", back_populates="purchase_order", cascade="all, delete-orphan")
    paid_by_user = relationship("User", foreign_keys=[paid_by_user_id])
