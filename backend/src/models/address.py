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
    is_primary = Column(Boolean, default=False)
    is_billing = Column(Boolean, default=False)
    is_shipping = Column(Boolean, default=False)
    
    # Relationship to user
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="addresses")
