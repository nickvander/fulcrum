from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class ExpenseReceipt(Base):
    __tablename__ = "expense_receipts"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    content_type = Column(String, nullable=True) # e.g. "application/pdf"
    file_size_bytes = Column(Integer, nullable=True)
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    expense = relationship("Expense", back_populates="receipts")
