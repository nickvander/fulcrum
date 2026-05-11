from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class SupplierDocumentImport(Base):
    __tablename__ = "supplier_document_imports"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    source = Column(String, default="supplier_document")
    status = Column(String, default="pending", index=True)
    mode = Column(String, default="create")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True, index=True)
    extracted_data = Column(JSON, nullable=False, default={})
    warnings = Column(JSON, nullable=False, default=[])
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
