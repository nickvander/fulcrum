"""
API Key model for external tool authentication.

Allows users to generate API keys for tools like Google Sheets Apps Script,
without sharing their JWT tokens.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Google Sheets Integration"
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    key_hash = Column(String, nullable=False)  # Hashed full key
    is_active = Column(Boolean, default=True)
    # FP-11: coarse scope. "full" (default, back-compat) = read+write; "read_only"
    # = rejected on write endpoints (require_write_scope). Enables least-privilege
    # integration keys (e.g. a CFDI-read-only key) without sharing a write key.
    scope = Column(String, nullable=False, server_default="full", default="full")
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration

    # Relationship
    user = relationship("User", backref="api_keys")
