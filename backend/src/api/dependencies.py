"""
FastAPI dependencies for the Fulcrum application.
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src import crud, models
from src.schemas import token as token_schema
from src.config import settings
from src.database import SessionLocal
from src.services.base import AIService
from src.services.dummy_ai_service import ai_service as dummy_ai_service
from src.models.api_key import ApiKey
from fastapi.security import APIKeyHeader
from datetime import datetime, timezone
import hashlib
import secrets

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/users/login/access-token"
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

reusable_oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/users/login/access-token",
    auto_error=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = token_schema.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = crud.user.get(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_user_optional(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2_optional)
) -> models.User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = token_schema.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        return None
    
    user = crud.user.get(db, id=token_data.sub)
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if current_user.user_type != "admin" and not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have admin privileges"
        )
    return current_user


def get_current_employee(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if current_user.user_type not in ["admin", "employee"]:
        raise HTTPException(
            status_code=403, detail="The user is not an employee"
        )
    return current_user


def get_current_customer(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=403, detail="The user is not a customer"
        )
    return current_user


def get_ai_service() -> AIService:
    """
    Returns the currently configured AI service.

    In a real application, this would read from a config file
    to determine which AI service implementation to return.
    """
    return dummy_ai_service


def get_current_user_with_api_key(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2_optional),
    api_key: str = Depends(api_key_header),
) -> models.User:
    """
    Authenticate using either OAuth2 token or X-API-Key header.
    API Key takes precedence if both are present.

    Records the caller's effective scope on ``request.state.api_key_scope``
    ("full" for JWT users and full keys, "read_only" for read-only keys) so
    ``require_write_scope`` can gate write endpoints (FP-11).
    """
    # 1. Try API Key
    if api_key:
        if len(api_key) < 8:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key format",
            )

        # Look up by prefix (optimization to avoid checking all hashes)
        prefix = api_key[:8]
        # We need to filter by prefix to limit candidates
        potential_keys = db.query(ApiKey).filter(
            ApiKey.key_prefix == prefix,
            ApiKey.is_active
        ).all()

        for db_key in potential_keys:
            # Hash the input key to compare with stored hash
            input_hash = hashlib.sha256(api_key.encode()).hexdigest()
            # Use constant-time comparison to prevent timing attacks
            if secrets.compare_digest(input_hash, db_key.key_hash):
                # FP-11: reject an expired key (the column existed but was never
                # enforced). expires_at is tz-aware; compare in UTC.
                if db_key.expires_at is not None and db_key.expires_at < datetime.now(
                    timezone.utc
                ):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API Key has expired",
                    )
                # Update usage stats + stash the scope for write-gating.
                db_key.last_used_at = datetime.utcnow()
                db.commit()
                request.state.api_key_scope = db_key.scope or "full"
                return db_key.user

        # If we had an API key but it failed validation
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    # 2. Try OAuth Token
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            token_data = token_schema.TokenPayload(**payload)
        except (jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
        user = crud.user.get(db, id=token_data.sub)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # This dependency authorizes STAFF (interactive admin/employee JWT) or the
        # storefront BFF (service X-API-Key) — every endpoint behind it is an
        # operator/service surface (order-create, returns record/transition,
        # inventory reservations, category writes, …). A CUSTOMER session JWT
        # (storefront magic-link) must NEVER authenticate here: customer
        # self-service goes through `get_current_customer`. Without this guard a
        # customer token would satisfy `require_write_scope` and could, e.g.,
        # self-transition its own return to `refunded` (crediting stock + stamping
        # a refund with no real money movement) or read operator data on any order.
        if getattr(user, "user_type", None) == "customer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this endpoint",
            )
        # JWT users are full-access (interactive admins/employees).
        request.state.api_key_scope = "full"
        return user

    # 3. No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def require_write_scope(
    request: Request,
    current_user: models.User = Depends(get_current_user_with_api_key),
) -> models.User:
    """Gate write endpoints: reject a read-only API key (FP-11).

    Depends on ``get_current_user_with_api_key`` (which authenticates AND records
    ``request.state.api_key_scope``), then rejects the call when that scope is not
    write-capable. JWT users and full-scope keys pass; only keys explicitly minted
    ``read_only`` are blocked, so existing (default "full") keys are unaffected.
    """
    scope = getattr(request.state, "api_key_scope", "full")
    if scope not in ("full", "write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key is read-only and cannot perform writes",
        )
    return current_user