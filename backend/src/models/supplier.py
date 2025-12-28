"""
SQLAlchemy models for the Supplier entity.
"""
from sqlalchemy import Column, Integer, String
from .base import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_person = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    
    # Address
    address_street = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    address_country = Column(String, nullable=True)

    # Financials
    tax_id = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True) # e.g. "Net 30"
    currency = Column(String, default="USD")

    # Details
    website = Column(String, nullable=True)
    internal_notes = Column(String, nullable=True)
