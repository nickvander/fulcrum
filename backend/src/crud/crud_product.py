from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from src.crud.base import CRUDBase
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate
from typing import List

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def get(self, db: Session, id: int) -> Product | None:
        return db.query(self.model).options(joinedload(self.model.images)).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        return (
            db.query(self.model)
            .options(joinedload(self.model.images))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_sku(self, db: Session, *, sku: str) -> Product | None:
        return db.query(Product).filter(Product.sku == sku).first()

    def create(self, db: Session, *, obj_in: ProductCreate) -> Product:
        if self.get_by_sku(db, sku=obj_in.sku):
            raise HTTPException(status_code=409, detail="Product with this SKU already exists.")
        return super().create(db, obj_in=obj_in)

    def search(self, db: Session, *, embedding: list[float], limit: int = 10) -> list[Product]:
        """
        Performs a vector similarity search for products.
        """
        return db.query(Product).order_by(Product.embedding.l2_distance(embedding)).limit(limit).all()

product = CRUDProduct(Product)
