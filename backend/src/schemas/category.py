"""Category taxonomy schemas (FP-07).

`slug` is optional on create — when omitted it's auto-generated from
`name` in the CRUD layer (lowercase, accent-stripped, hyphenated, with a
numeric suffix on collision). The `Category` response carries a computed
`product_count` and a nested `children` list (populated only when the
endpoint is asked for the tree).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None  # auto-generated from name when omitted
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Number of products linked via products.category_id. Populated by
    # the list/detail endpoints; defaults to 0 so a bare model_validate
    # of an ORM row doesn't blow up.
    product_count: int = 0
    # Nested children — populated only when the endpoint builds the tree
    # (`GET /categories?tree=true`); empty otherwise.
    children: List["Category"] = []


Category.model_rebuild()
