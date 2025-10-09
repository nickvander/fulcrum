from src.crud.base import CRUDBase
from src.models.product import ProductImage
from src.schemas.product import ProductImageCreate, ProductImageUpdate

class CRUDProductImage(CRUDBase[ProductImage, ProductImageCreate, ProductImageUpdate]):
    pass

product_image = CRUDProductImage(ProductImage)
