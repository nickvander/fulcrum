from datetime import datetime, timedelta
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from src.config import settings

# Configure Argon2 with balanced security parameters
# Tuned for Docker environment while maintaining strong security
# - argon2id: Hybrid mode (best of argon2i and argon2d)
# - memory_cost: 8 MiB (reduced further for Docker testing stability)
# - time_cost: 1 iteration (minimal for testing)
# - parallelism: 1 thread (minimal for testing)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=8192,  # 8 MiB
    argon2__time_cost=1,
    argon2__parallelism=1,
    argon2__type="ID"  # Use Argon2id variant
)


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
