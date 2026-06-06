"""Category taxonomy CRUD (FP-07).

Owns slug generation (lowercase, accent-stripped, hyphenated, with a
numeric suffix on collision) and the hierarchy-aware listing used by the
public `/categories` endpoint. `product_count` is computed on demand via
a batched aggregate so a list of categories costs one extra query, not
one-per-row.
"""
import re
import unicodedata
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.category import Category
from src.models.product import Product
from src.schemas.category import CategoryCreate, CategoryUpdate


def slugify(value: str) -> str:
    """lowercase, strip accents, hyphenate. Mirrors the storefront's
    slug expectations: 'Electrónica' -> 'electronica', 'Hogar y Cocina'
    -> 'hogar-y-cocina'."""
    # Decompose accented chars and drop the combining marks.
    normalized = unicodedata.normalize("NFKD", value)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_str = ascii_str.lower().strip()
    # Replace any run of non-alphanumerics with a single hyphen.
    ascii_str = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return ascii_str.strip("-")


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    def get_by_slug(self, db: Session, *, slug: str) -> Optional[Category]:
        return db.query(Category).filter(Category.slug == slug).first()

    def list(
        self,
        db: Session,
        *,
        parent_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        include_descendants_parent_filter: bool = True,
    ) -> List[Category]:
        """List categories ordered by (sort_order, name).

        `parent_id` filters to direct children of that parent. Pass
        `parent_id` explicitly as `None` together with
        `include_descendants_parent_filter=True` (the default for the
        caller that wants top-level roots) to get only roots — but note
        the endpoint distinguishes "no filter" from "roots only" itself,
        so this method only applies the filter when asked.
        """
        query = db.query(Category)
        if is_active is not None:
            query = query.filter(Category.is_active == is_active)
        if parent_id is not None:
            query = query.filter(Category.parent_id == parent_id)
        return query.order_by(Category.sort_order, Category.name).all()

    def list_all(
        self, db: Session, *, is_active: Optional[bool] = None
    ) -> List[Category]:
        query = db.query(Category)
        if is_active is not None:
            query = query.filter(Category.is_active == is_active)
        return query.order_by(Category.sort_order, Category.name).all()

    def list_roots(
        self, db: Session, *, is_active: Optional[bool] = None
    ) -> List[Category]:
        query = db.query(Category).filter(Category.parent_id.is_(None))
        if is_active is not None:
            query = query.filter(Category.is_active == is_active)
        return query.order_by(Category.sort_order, Category.name).all()

    def product_counts(self, db: Session) -> Dict[int, int]:
        """Map of category_id -> number of products linked via
        products.category_id. One aggregate query for the whole set."""
        rows = (
            db.query(
                Product.category_id,
                func.count(Product.id).label("cnt"),
            )
            .filter(Product.category_id.isnot(None))
            .group_by(Product.category_id)
            .all()
        )
        return {row.category_id: int(row.cnt) for row in rows}

    def _unique_slug(self, db: Session, base: str) -> str:
        """Return `base`, or `base-2`, `base-3`, ... until unique."""
        if not base:
            base = "categoria"
        candidate = base
        suffix = 2
        while self.get_by_slug(db, slug=candidate) is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def create(self, db: Session, *, obj_in: CategoryCreate) -> Category:
        data = obj_in.model_dump()
        slug = data.get("slug")
        if slug:
            slug = slugify(slug)
        if not slug:
            slug = slugify(data["name"])
        data["slug"] = self._unique_slug(db, slug)
        db_obj = Category(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Category, obj_in: CategoryUpdate
    ) -> Category:
        update_data = obj_in.model_dump(exclude_unset=True)
        # If the caller passes a slug, normalize + dedupe it (excluding
        # the row itself). If they don't, leave the existing slug alone.
        if "slug" in update_data and update_data["slug"]:
            new_slug = slugify(update_data["slug"])
            existing = self.get_by_slug(db, slug=new_slug)
            if existing is not None and existing.id != db_obj.id:
                new_slug = self._unique_slug(db, new_slug)
            update_data["slug"] = new_slug
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


category = CRUDCategory(Category)
