from src.crud.base import CRUDBase
from src.models.product import Product
from src.schemas.product import ProductCreate

class CRUDProduct(CRUDBase[Product, ProductCreate]):
    pass

product = CRUDProduct(Product)
