"""Category taxonomy (FP-07).

Promotes the legacy free-text `products.category` string to a real
hierarchical taxonomy table. A `Category` can nest under a parent via
`parent_id` (self-FK); deleting a parent sets its children's
`parent_id` to NULL rather than cascading the delete, so a mistaken
delete never wipes a whole subtree of products' classification.

The legacy `Product.category` string column is intentionally KEPT for
back-compat; `Product.category_id` is the new authoritative link and is
nullable (a product can be uncategorized; deleting its category sets it
back to NULL via ondelete=SET NULL).
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    parent_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Self-referential hierarchy. `remote_side` points at the PK so
    # SQLAlchemy knows `parent_id` is the "many" side.
    parent = relationship(
        "Category", remote_side=[id], back_populates="children"
    )
    children = relationship(
        "Category",
        back_populates="parent",
        order_by="Category.sort_order, Category.name",
    )

    # Products linked to this category. No cascade-delete: the FK's
    # ondelete=SET NULL handles orphaning at the DB level.
    products = relationship("Product", back_populates="category_ref")
