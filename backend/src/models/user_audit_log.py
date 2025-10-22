from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from sqlalchemy import ForeignKey


class UserAuditLog(Base):
    __tablename__ = "user_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # The user that the action was performed on
    action_performed_by = Column(Integer, ForeignKey("users.id"))  # The user who performed the action
    action = Column(String, index=True)  # e.g., 'create', 'update', 'delete', 'password_reset'
    details = Column(Text)  # Additional details about the action
    ip_address = Column(String)  # IP address of the user who performed the action
    user_agent = Column(String)  # User agent of the user who performed the action
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to the user that was affected
    user = relationship("User", foreign_keys=[user_id], back_populates="audit_logs")
    # Relationship to the user who performed the action
    actor = relationship("User", foreign_keys=[action_performed_by], back_populates="performed_audit_logs")


