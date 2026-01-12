from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    category = Column(String, index=True)  # e.g., "Marketing", "Software", "Rent", "Shipping"
    is_custom_category = Column(Boolean, default=False)  # True if user-created category
    date = Column(Date, index=True)
    
    # Expense type: one_time or recurring
    expense_type = Column(String, default="one_time")  # "one_time" or "recurring"
    recurrence_interval = Column(String, nullable=True)  # "weekly", "monthly", "quarterly", "yearly"
    
    # Additional tracking fields
    reference_number = Column(String, nullable=True)  # Invoice/receipt reference
    payment_method = Column(String, nullable=True)  # "cash", "card", "transfer", "check"
    notes = Column(Text, nullable=True)
    
    # User who paid (for reimbursement tracking)
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_by_name = Column(String, nullable=True)  # For non-system users/contributors
    is_reimbursed = Column(Boolean, default=False)
    reimbursed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optional associations
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paid_by_user = relationship("User")
    product = relationship("Product")
    supplier = relationship("Supplier")

    purchase_order = relationship("PurchaseOrder")
    receipts = relationship("ExpenseReceipt", back_populates="expense", cascade="all, delete-orphan")


