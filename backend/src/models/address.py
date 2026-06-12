from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    country = Column(String, nullable=False)
    # Mexican-address granularity + shipping prefill (FP-B). `colonia` (the
    # neighborhood) and `interior` (apartment/unit) are required by MX carriers
    # for reliable delivery; `recipient_name`/`phone` make a saved address
    # self-sufficient as a ship-to (the recipient is not always the account
    # holder). All nullable — legacy rows simply lack them. PII: never logged.
    colonia = Column(String(128), nullable=True)
    interior = Column(String(32), nullable=True)
    recipient_name = Column(String(128), nullable=True)
    phone = Column(String(20), nullable=True)
    is_primary = Column(Boolean, default=False)
    is_billing = Column(Boolean, default=False)
    is_shipping = Column(Boolean, default=False)
    
    # Relationship to user
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="addresses")
