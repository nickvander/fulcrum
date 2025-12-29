from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.store_settings import StoreSettings
from src.schemas.store_settings import StoreSettingsCreate, StoreSettingsUpdate

class CRUDStoreSettings(CRUDBase[StoreSettings, StoreSettingsCreate, StoreSettingsUpdate]):
    def get_settings(self, db: Session) -> StoreSettings:
        settings = db.query(self.model).first()
        if not settings:
            # Create default
            settings = self.create(db, obj_in=StoreSettingsCreate())
        return settings

store_settings = CRUDStoreSettings(StoreSettings)
