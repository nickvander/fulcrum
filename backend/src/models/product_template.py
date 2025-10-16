from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class ProductTemplate(Base):
    __tablename__ = "product_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    brand = Column(String)
    default_resale_price = Column(Float)
    cost_price = Column(Float)
    manufacturer = Column(String)
    width = Column(Float)
    height = Column(Float)
    depth = Column(Float)
    weight = Column(Float)
    properties = Column(String)  # JSON string for additional properties
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to custom fields associated with this template
    custom_fields = relationship("CustomFieldTemplate", back_populates="template", cascade="all, delete-orphan")