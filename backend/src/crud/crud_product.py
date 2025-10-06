from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def search(self, db: Session, *, embedding: list[float], limit: int = 10) -> list[Product]:
        """
        Performs a vector similarity search for products.
        """
        return db.query(Product).order_by(Product.embedding.l2_distance(embedding)).limit(limit).all()

product = CRUDProduct(Product)
