from src.crud.base import CRUDBase
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import get_password_hash
from sqlalchemy.orm import Session

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

user = CRUDUser(User)
