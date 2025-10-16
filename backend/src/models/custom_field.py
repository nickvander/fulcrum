from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base

class FieldType(enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"

class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    type = Column(Enum(FieldType))

class ProductCustomField(Base):
    __tablename__ = "product_custom_fields"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    custom_field_id = Column(Integer, ForeignKey("custom_fields.id"))
    value = Column(String)

    product = relationship("Product", back_populates="custom_fields")
    custom_field = relationship("CustomField")
