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

    def update(
        self,
        db: Session,
        *,
        db_obj: StoreSettings,
        obj_in: StoreSettingsUpdate | dict
    ) -> StoreSettings:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "ai_enabled" in update_data and update_data["ai_enabled"] is not None:
             update_data["ai_enabled"] = 1 if update_data["ai_enabled"] else 0

        from src.core.encryption import encryption_service

        # Encrypt AI API keys if they are being updated
        ai_keys = [
            "ai_google_api_key",
            "ai_openai_api_key",
            "ai_anthropic_api_key",
            "ai_qwen_api_key"
        ]
        
        for key in ai_keys:
            if key in update_data and update_data[key]:
                # Encrypt the raw key provided by frontend
                update_data[key] = encryption_service.encrypt(update_data[key])

        return super().update(db, db_obj=db_obj, obj_in=update_data)

store_settings = CRUDStoreSettings(StoreSettings)

