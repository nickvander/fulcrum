from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.schemas import user as user_schema
from src.database import get_db
from src.crud import crud_user

router = APIRouter()

@router.post("/", response_model=user_schema.User, tags=["users"])
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    # In a real app, you'd check if the user already exists
    return crud_user.user.create(db=db, obj_in=user)
