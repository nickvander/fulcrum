from src.crud.base import CRUDBase
from src.models.product_variant import ProductVariant
from src.schemas.product_variant import ProductVariantCreate, ProductVariantUpdate
from typing import List


class CRUDProductVariant(CRUDBase[ProductVariant, ProductVariantCreate, ProductVariantUpdate]):
    def get_by_product_id(self, db, *, product_id: int) -> List[ProductVariant]:
        """Get all variants for a specific product."""
        return db.query(self.model).filter(self.model.product_id == product_id).all()

    def get_by_sku(self, db, *, sku: str) -> ProductVariant | None:
        """Get a variant by its SKU."""
        return db.query(self.model).filter(self.model.sku == sku).first()


product_variant = CRUDProductVariant(ProductVariant)