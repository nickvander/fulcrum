from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
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
