from src.crud.base import CRUDBase
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import get_password_hash
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        logger.info(f"Creating user with email: {obj_in.email}")
        try:
            hashed_password = get_password_hash(obj_in.password)
            logger.info("Password hashed successfully.")
            db_obj = User(
                email=obj_in.email,
                hashed_password=hashed_password,
            )
            db.add(db_obj)
            logger.info("User object added to session.")
            db.commit()
            logger.info("Session committed.")
            db.refresh(db_obj)
            logger.info("DB object refreshed.")
            return db_obj
        except Exception as e:
            logger.error(f"Error in CRUDUser.create: {e}", exc_info=True)
            db.rollback()
            raise

user = CRUDUser(User)
