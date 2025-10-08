from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from src.schemas import user as user_schema
from src.database import get_db
from src.crud import crud_user

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/", response_model=user_schema.User, tags=["users"])
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    logger.info("Attempting to create user...")
    try:
        # In a real app, you'd check if the user already exists
        created_user = crud_user.user.create(db=db, obj_in=user)
        logger.info("User created successfully.")
        return created_user
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise
