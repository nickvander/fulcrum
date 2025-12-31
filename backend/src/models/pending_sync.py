"""
Pending Sync models for staged sync workflow from external sources.

This module provides:
1. SyncBatch - Tracks a batch of sync operations (lightweight history)
2. PendingSyncChange - Individual changes within a batch (deleted after processing)
3. EntityChangeLog - Audit trail for all entity changes with source attribution
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta

from .base import Base


class SyncBatch(Base):
    """
    Tracks a batch of sync changes - lightweight history without bloat.
    
    Each push from Google Sheets (or other external sources) creates one batch.
    The batch persists for audit purposes even after individual changes are processed.
    """
    __tablename__ = "sync_batches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String(50), nullable=False, index=True)  # "google_sheets", "csv_import"
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, approved, rejected, partial
    total_changes = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For auto-cleanup

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])
    changes = relationship("PendingSyncChange", back_populates="batch", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default expiry to 30 days from creation
        if self.expires_at is None:
            self.expires_at = datetime.utcnow() + timedelta(days=30)


class PendingSyncChange(Base):
    """
    Individual change within a batch - deleted after batch is processed.
    
    Stores the proposed change with old/new values for preview and review.
    """
    __tablename__ = "pending_sync_changes"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("sync_batches.id", ondelete="CASCADE"), nullable=False)
    entity = Column(String(50), nullable=False, index=True)  # "products", "inventory"
    entity_id = Column(Integer, nullable=False, index=True)  # Product ID, etc.
    entity_name = Column(String(255), nullable=True)  # "Blue Widget" for preview (denormalized)
    entity_sku = Column(String(100), nullable=True)  # SKU for easy identification
    field = Column(String(100), nullable=False)  # "cost_price", "resale_price", "name"
    old_value = Column(Text, nullable=True)  # Current value in Fulcrum
    new_value = Column(Text, nullable=True)  # Proposed new value
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected

    # Relationship
    batch = relationship("SyncBatch", back_populates="changes")


class EntityChangeLog(Base):
    """
    Audit trail for entity changes. Tracks WHO changed WHAT and 
    importantly WHERE the change came from (source).
    
    This provides full traceability for all changes, allowing queries like:
    - "Show me all price changes from Sheets imports"
    - "Who changed this product's cost, and was it from Sheets or manual?"
    """
    __tablename__ = "entity_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # "product", "supplier", "inventory"
    entity_id = Column(Integer, nullable=False, index=True)  # The ID of the changed entity
    entity_name = Column(String(255), nullable=True)  # Denormalized for readability
    field = Column(String(100), nullable=False)  # "cost_price", "resale_price", etc.
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, index=True)  # "sheets_import", "direct_edit", "api"
    source_batch_id = Column(Integer, ForeignKey("sync_batches.id", ondelete="SET NULL"), nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6

    # Relationships
    changed_by = relationship("User")
    source_batch = relationship("SyncBatch")
