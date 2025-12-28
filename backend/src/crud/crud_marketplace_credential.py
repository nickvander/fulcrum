from typing import Optional, List
from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.marketplace import MarketplaceCredential
from src.schemas.marketplace_credential import MarketplaceCredentialCreate, MarketplaceCredentialUpdate
from src.core.encryption import encryption_service

class CRUDMarketplaceCredential(CRUDBase[MarketplaceCredential, MarketplaceCredentialCreate, MarketplaceCredentialUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: MarketplaceCredentialCreate, user_id: int
    ) -> MarketplaceCredential:
        """
        Create a new credential for a specific user, encrypting the tokens first.
        """
        db_obj = MarketplaceCredential(
            marketplace_id=obj_in.marketplace_id,
            user_id=user_id,
            access_token=encryption_service.encrypt(obj_in.access_token),
            refresh_token=encryption_service.encrypt(obj_in.refresh_token),
            token_type=obj_in.token_type,
            scopes=obj_in.scopes,
            expires_at=obj_in.expires_at
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_marketplace(
        self, db: Session, *, user_id: int, marketplace_id: int
    ) -> Optional[MarketplaceCredential]:
        """
        Fetch credentials for a specific user and marketplace.
        """
        return db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.marketplace_id == marketplace_id
        ).first()

    def get_multi_by_owner(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[MarketplaceCredential]:
        """
        Fetch all credentials for a specific user.
        """
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).offset(skip).limit(limit).all()

    def update_with_encryption(
        self, db: Session, *, db_obj: MarketplaceCredential, obj_in: MarketplaceCredentialUpdate
    ) -> MarketplaceCredential:
        """
        Update credentials, encrypting tokens if they are provided.
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        if "access_token" in update_data:
            update_data["access_token"] = encryption_service.encrypt(update_data["access_token"])
        if "refresh_token" in update_data:
            update_data["refresh_token"] = encryption_service.encrypt(update_data["refresh_token"])
        
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_decrypted_access_token(self, db_obj: MarketplaceCredential) -> str:
        """
        Helper to decrypt the access token for internal use.
        """
        return encryption_service.decrypt(db_obj.access_token)

    def get_decrypted_refresh_token(self, db_obj: MarketplaceCredential) -> str:
        """
        Helper to decrypt the refresh token for internal use.
        """
        return encryption_service.decrypt(db_obj.refresh_token)

marketplace_credential = CRUDMarketplaceCredential(MarketplaceCredential)
