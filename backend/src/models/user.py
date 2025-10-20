from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    employee_id = Column(String, unique=True, index=True)  # Auto-generated employee ID
    first_name = Column(String)
    last_name = Column(String)
    user_type = Column(String)  # admin, employee, customer
    is_active = Column(Boolean, default=True)  # Track if user account is active
    is_superuser = Column(Boolean, default=False)
    role = Column(String)  # Keep existing role field
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to addresses
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship to password reset tokens
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship to audit logs (what happened to this user)
    audit_logs = relationship("UserAuditLog", foreign_keys="UserAuditLog.user_id", back_populates="user", cascade="all, delete-orphan")
    # Relationship to audit logs (what this user did to others)
    performed_audit_logs = relationship("UserAuditLog", foreign_keys="UserAuditLog.action_performed_by", back_populates="actor", cascade="all, delete-orphan")
