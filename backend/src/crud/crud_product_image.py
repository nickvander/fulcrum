from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.product import ProductImage
from src.schemas.product import ProductImageCreate, ProductImageUpdate

class CRUDProductImage(CRUDBase[ProductImage, ProductImageCreate, ProductImageUpdate]):
    def set_primary_image(
        self, db: Session, *, product_id: int, image_id: int
    ) -> ProductImage:
        """
        Sets a specific image as the primary image for a product,
        ensuring all other images for that product are not set as primary.
        """
        # Unset all other primary images for this product
        db.query(self.model).filter(
            self.model.product_id == product_id
        ).update({"is_primary": 0})

        # Set the new primary image
        db_obj = db.query(self.model).filter(
            self.model.id == image_id,
            self.model.product_id == product_id
        ).first()

        if db_obj:
            db_obj.is_primary = 1
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        
        return db_obj

product_image = CRUDProductImage(ProductImage)
