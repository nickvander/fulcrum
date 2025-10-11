import pytest
from sqlalchemy.orm import Session

from src.crud import crud_user
from src.schemas.user import UserCreate


@pytest.mark.db
def test_create_superuser(db: Session) -> None:
    """
    Tests that a superuser can be created correctly.
    """
    user_in = UserCreate(
        email="superuser@example.com",
        password="password123",
        is_superuser=True,
    )
    user = crud_user.user.create(db, obj_in=user_in)
    assert user
    assert user.is_superuser
    assert user.email == "superuser@example.com"
