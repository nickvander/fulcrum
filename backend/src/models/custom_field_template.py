from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class CustomFieldTemplate(Base):
    __tablename__ = "custom_field_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="text")  # text, number, boolean, etc.
    default_value = Column(String)
    required = Column(Integer, default=0)  # 0 for false, 1 for true

    # Relationship to template
    template = relationship("ProductTemplate", back_populates="custom_fields")