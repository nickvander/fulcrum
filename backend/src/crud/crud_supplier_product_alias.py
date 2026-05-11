import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from src.crud.base import CRUDBase
from src.models.supplier_product_alias import SupplierProductAlias
from src.schemas.supplier_product_alias import SupplierProductAliasCreate, SupplierProductAliasUpdate


def normalize_alias_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return normalized or None


class CRUDSupplierProductAlias(
    CRUDBase[SupplierProductAlias, SupplierProductAliasCreate, SupplierProductAliasUpdate]
):
    def get_active_by_supplier(self, db: Session, *, supplier_id: int) -> list[SupplierProductAlias]:
        return (
            db.query(self.model)
            .options(joinedload(self.model.product), joinedload(self.model.variant))
            .filter(self.model.supplier_id == supplier_id, self.model.is_active.is_(True))
            .order_by(self.model.updated_at.desc(), self.model.id.desc())
            .all()
        )

    def get_active_by_supplier_and_product(
        self, db: Session, *, supplier_id: int, product_id: int
    ) -> list[SupplierProductAlias]:
        return (
            db.query(self.model)
            .options(joinedload(self.model.product), joinedload(self.model.variant))
            .filter(
                self.model.supplier_id == supplier_id,
                self.model.product_id == product_id,
                self.model.is_active.is_(True),
            )
            .order_by(self.model.updated_at.desc(), self.model.id.desc())
            .all()
        )

    def upsert_learned_alias(
        self,
        db: Session,
        *,
        supplier_id: int,
        product_id: int,
        variant_id: Optional[int] = None,
        alias_sku: str | None = None,
        alias_name: str | None = None,
        source: str = "po_confirmation",
        confidence: float = 1.0,
    ) -> SupplierProductAlias | None:
        normalized_sku = normalize_alias_text(alias_sku)
        normalized_name = normalize_alias_text(alias_name)
        if not normalized_sku and not normalized_name:
            return None

        alias_filters = []
        if normalized_sku:
            alias_filters.append(self.model.normalized_sku == normalized_sku)
        if normalized_name:
            alias_filters.append(self.model.normalized_name == normalized_name)

        query = db.query(self.model).filter(self.model.supplier_id == supplier_id)
        if len(alias_filters) == 2:
            existing = query.filter(alias_filters[0] | alias_filters[1]).first()
        else:
            existing = query.filter(alias_filters[0]).first()

        if existing:
            existing.product_id = product_id
            existing.variant_id = variant_id
            existing.alias_sku = alias_sku
            existing.alias_name = alias_name
            existing.normalized_sku = normalized_sku
            existing.normalized_name = normalized_name
            existing.source = source
            existing.confidence = confidence
            existing.is_active = True
            db.add(existing)
            db.flush()
            return existing

        alias = self.model(
            supplier_id=supplier_id,
            product_id=product_id,
            variant_id=variant_id,
            alias_sku=alias_sku,
            alias_name=alias_name,
            normalized_sku=normalized_sku,
            normalized_name=normalized_name,
            source=source,
            confidence=confidence,
            is_active=True,
        )
        db.add(alias)
        db.flush()
        return alias

    def mark_matched(self, db: Session, *, alias: SupplierProductAlias) -> SupplierProductAlias:
        alias.match_count = (alias.match_count or 0) + 1
        alias.last_matched_at = datetime.now(timezone.utc)
        db.add(alias)
        db.flush()
        return alias

    def deactivate(self, db: Session, *, id: int) -> SupplierProductAlias | None:
        alias = self.get(db, id=id)
        if not alias:
            return None
        alias.is_active = False
        db.add(alias)
        db.commit()
        db.refresh(alias)
        return alias


supplier_product_alias = CRUDSupplierProductAlias(SupplierProductAlias)
