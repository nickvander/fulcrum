from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from src import crud, models
from src.schemas import token as token_schema, user as user_schema
from src.api import dependencies
from src.config import settings
from src.core import security

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/", response_model=user_schema.User, tags=["users"])
def create_user(
    *,
    db: Session = Depends(dependencies.get_db),
    user_in: user_schema.UserCreate,
) -> models.User:
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db, obj_in=user_in)
    return user


@router.post("/login/access-token", response_model=token_schema.Token, tags=["users"])
def login_access_token(
    db: Session = Depends(dependencies.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/", response_model=List[user_schema.User], tags=["users"])
def read_users(
    db: Session = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_superuser),
) -> List[models.User]:
    """
    Retrieve users.
    """
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=user_schema.User, tags=["users"])
def read_user_by_id(
    user_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
) -> models.User:
    """
    Get a specific user by id.
    """
    user = crud.user.get(db, id=user_id)
    if user == current_user:
        return user
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return user


@router.put("/{user_id}", response_model=user_schema.User, tags=["users"])
def update_user(
    *,
    db: Session = Depends(dependencies.get_db),
    user_id: int,
    user_in: user_schema.UserUpdate,
    current_user: models.User = Depends(dependencies.get_current_superuser),
) -> models.User:
    """
    Update a user.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    user = crud.user.update(db, db_obj=user, obj_in=user_in)
    return user
