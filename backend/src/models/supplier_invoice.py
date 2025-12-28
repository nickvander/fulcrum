from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class SupplierInvoice(Base):
    __tablename__ = "supplier_invoices"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))
    
    invoice_number = Column(String, index=True, nullable=True)
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    
    file_path = Column(String, nullable=True) # Path to stored PDF/Image
    parsed_data = Column(Text, nullable=True) # JSON string of AI extracted data
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    purchase_order = relationship("PurchaseOrder", back_populates="invoices")
