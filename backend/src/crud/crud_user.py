from typing import Optional
from src.crud.base import CRUDBase
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import get_password_hash, verify_password
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        logger.info(f"Creating user with email: {obj_in.email}")
        try:
            hashed_password = get_password_hash(obj_in.password)
            logger.info("Password hashed successfully.")
            db_obj = User(
                email=obj_in.email,
                hashed_password=hashed_password,
                is_superuser=obj_in.is_superuser,
            )
            db.add(db_obj)
            logger.info("User object added to session.")
            db.flush()
            logger.info("Session flushed.")
            db.refresh(db_obj)
            logger.info("DB object refreshed.")
            return db_obj
        except Exception as e:
            logger.error(f"Error in CRUDUser.create: {e}", exc_info=True)
            db.rollback()
            raise

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser

user = CRUDUser(User)
