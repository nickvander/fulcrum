"""Category taxonomy API (FP-07).

Mounted at `/api/v1/categories`. Reads are PUBLIC (the storefront/BFF
needs the nav tree without auth); writes require an authenticated user
OR an X-API-Key (`get_current_user_with_api_key`) so the server-to-server
BFF can manage the taxonomy.

`product_count` is hydrated on every read via one batched aggregate.
`?tree=true` returns the nested hierarchy (roots with `children`);
otherwise a flat ordered list is returned.
"""
import contextvars
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api import dependencies
from src.api.dependencies import get_db
from src.core.errors import LocalizedHTTPException
from src.crud import crud_category
from src.models.user import User
from src.schemas.category import (
    Category as CategorySchema,
    CategoryCreate,
    CategoryUpdate,
)


router = APIRouter()


# A tiny context flag so the recursive `_to_schema` helper knows whether
# the current request asked to include inactive nodes when walking
# children. Using a ContextVar keeps the helper signature clean.
_INCLUDE_INACTIVE: contextvars.ContextVar = contextvars.ContextVar(
    "categories_include_inactive", default=False
)


def _to_schema(cat, counts: dict, *, with_children: bool = False) -> CategorySchema:
    """Serialize an ORM category, injecting product_count (and, for the
    tree view, recursively serialized children)."""
    schema = CategorySchema.model_validate(cat)
    schema.product_count = counts.get(cat.id, 0)
    if with_children:
        schema.children = [
            _to_schema(child, counts, with_children=True)
            for child in sorted(
                cat.children, key=lambda c: (c.sort_order, c.name)
            )
            # In the tree, hide inactive children unless the whole list
            # was requested with include_inactive (handled by the caller
            # pre-filtering the root set; children are filtered here).
            if child.is_active or _INCLUDE_INACTIVE.get()
        ]
    return schema


@router.get("", response_model=List[CategorySchema])
def list_categories(
    *,
    db: Session = Depends(get_db),
    parent_id: Optional[int] = None,
    include_inactive: bool = False,
    tree: bool = False,
):
    """PUBLIC. List categories ordered by (sort_order, name) with
    product_count populated.

    - `tree=true`: nested hierarchy (roots with recursive `children`).
      `parent_id` is ignored in tree mode.
    - `parent_id`: flat list of that parent's direct children. Pass
      `parent_id=0`-less (omit) for the full flat list.
    - `include_inactive`: include is_active=false rows (default false).
    """
    is_active_filter = None if include_inactive else True
    counts = crud_category.category.product_counts(db)
    token = _INCLUDE_INACTIVE.set(include_inactive)
    try:
        if tree:
            roots = crud_category.category.list_roots(
                db, is_active=is_active_filter
            )
            return [
                _to_schema(root, counts, with_children=True) for root in roots
            ]
        if parent_id is not None:
            cats = crud_category.category.list(
                db, parent_id=parent_id, is_active=is_active_filter
            )
        else:
            cats = crud_category.category.list_all(db, is_active=is_active_filter)
        return [_to_schema(cat, counts) for cat in cats]
    finally:
        _INCLUDE_INACTIVE.reset(token)


@router.get("/{slug}", response_model=CategorySchema)
def get_category(
    slug: str,
    *,
    db: Session = Depends(get_db),
):
    """PUBLIC. Fetch a single category by slug. 404 if missing."""
    cat = crud_category.category.get_by_slug(db, slug=slug)
    if cat is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.category.notFound",
            params={"slug": slug},
            detail="Category not found",
        )
    counts = crud_category.category.product_counts(db)
    return _to_schema(cat, counts)


@router.post("", response_model=CategorySchema)
def create_category(
    *,
    db: Session = Depends(get_db),
    obj_in: CategoryCreate,
    current_user: User = Depends(dependencies.require_write_scope),
):
    """Create a category. Authed (JWT or X-API-Key). If a provided slug
    already exists -> 409. Omitted slug is auto-generated from name."""
    if obj_in.slug:
        from src.crud.crud_category import slugify

        existing = crud_category.category.get_by_slug(
            db, slug=slugify(obj_in.slug)
        )
        if existing is not None:
            raise LocalizedHTTPException(
                status_code=409,
                code="apiErrors.category.slugExists",
                params={"slug": obj_in.slug},
                detail="A category with this slug already exists.",
            )
    cat = crud_category.category.create(db, obj_in=obj_in)
    counts = crud_category.category.product_counts(db)
    return _to_schema(cat, counts)


@router.put("/{category_id}", response_model=CategorySchema)
def update_category(
    category_id: int,
    obj_in: CategoryUpdate,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
):
    """Update a category. Authed (JWT or X-API-Key). 404 if missing;
    409 if the new slug collides with another category."""
    cat = crud_category.category.get(db, id=category_id)
    if cat is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.category.notFound",
            params={"id": category_id},
            detail="Category not found",
        )
    if obj_in.slug:
        from src.crud.crud_category import slugify

        existing = crud_category.category.get_by_slug(
            db, slug=slugify(obj_in.slug)
        )
        if existing is not None and existing.id != category_id:
            raise LocalizedHTTPException(
                status_code=409,
                code="apiErrors.category.slugExists",
                params={"slug": obj_in.slug},
                detail="A category with this slug already exists.",
            )
    cat = crud_category.category.update(db, db_obj=cat, obj_in=obj_in)
    counts = crud_category.category.product_counts(db)
    return _to_schema(cat, counts)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.require_write_scope),
):
    """Delete a category. Authed (JWT or X-API-Key). 404 if missing.
    The FK ondelete=SET NULL nulls children's parent_id and products'
    category_id automatically."""
    cat = crud_category.category.get(db, id=category_id)
    if cat is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.category.notFound",
            params={"id": category_id},
            detail="Category not found",
        )
    crud_category.category.remove(db, id=category_id)
    return {"deleted": category_id}
