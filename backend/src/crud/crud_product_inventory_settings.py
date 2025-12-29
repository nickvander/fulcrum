from typing import Optional
from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.product_inventory_settings import ProductInventorySettings
from src.schemas.product_inventory_settings import ProductInventorySettingsCreate, ProductInventorySettingsUpdate

class CRUDProductInventorySettings(CRUDBase[ProductInventorySettings, ProductInventorySettingsCreate, ProductInventorySettingsUpdate]):
    def get_by_product(self, db: Session, *, product_id: int) -> Optional[ProductInventorySettings]:
        return db.query(self.model).filter(self.model.product_id == product_id).first()

product_inventory_settings = CRUDProductInventorySettings(ProductInventorySettings)
