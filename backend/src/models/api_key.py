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
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration

    # Relationship
    user = relationship("User", backref="api_keys")
