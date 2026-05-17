from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class CatalogImport(Base):
    """
    Staging row for AI/CSV catalog imports.

    Mirrors the shape of `SupplierDocumentImport` so the upload → preview →
    approve flow is consistent across importers, but approval here creates
    `Product` rows (and optional `SupplierProduct` links) instead of a
    PurchaseOrder.

    `source`:
      - "csv"  — CSV / spreadsheet upload (v1)
      - "pdf"  — AI-extracted from a PDF catalog (follow-up)

    `extracted_data` JSON shape: {"items": [<ExtractedCatalogItem dicts>]}
    Each item carries the parsed fields plus a `selected` flag the user can
    toggle in the review dialog.
    """

    __tablename__ = "catalog_imports"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    source = Column(String, default="csv")
    status = Column(String, default="pending", index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    extracted_data = Column(JSON, nullable=False, default={})
    warnings = Column(JSON, nullable=False, default=[])
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    supplier = relationship("Supplier")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
