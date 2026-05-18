"""
ImportTemplate persists a per-supplier mapping of "source CSV headers ->
Fulcrum canonical fields" so a user who imports the same supplier's
catalog every month doesn't have to re-map columns each time.

The template lives independently of the catalog_imports table — picking a
template at upload time just overrides the auto-detected header map.
Adding the same model for purchase-order imports or other sources later
is a matter of adding new `source_type` values; the schema stays.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ImportTemplate(Base):
    """
    A named column mapping for a specific kind of import.

    `column_map` shape: {<source header>: <fulcrum field>}, e.g.
        {"Item No.": "sku", "Product Description": "name", "Cost USD": "cost_price"}

    `source_type` is currently only "catalog" but is a string column so
    future importers (PO, expense, sales) can reuse the same table.
    """

    __tablename__ = "import_templates"
    __table_args__ = (
        # Names are unique per user + source so two users can have a "ProSupply"
        # template that means different things, but one user can't.
        UniqueConstraint("created_by_id", "source_type", "name", name="uq_import_template_owner_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False, default="catalog", index=True)
    column_map = Column(JSON, nullable=False, default={})
    notes = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])
