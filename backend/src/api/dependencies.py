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


def _authenticate_api_key(
    request: Request, db: Session, api_key: str | None
) -> models.User | None:
    """Resolve a caller from the ``X-API-Key`` header.

    Returns the key's owning user (and stashes the key's scope on
    ``request.state.api_key_scope`` for ``require_write_scope``) when a valid,
    unexpired key is present; returns ``None`` when no api-key header is supplied;
    raises 401 on a malformed / invalid / expired key. Shared by the auth-or-key
    dependencies below so the (security-sensitive) key check lives in one place.
    """
    if not api_key:
        return None
    if len(api_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format",
        )
    # Look up by prefix (optimization to avoid checking all hashes).
    prefix = api_key[:8]
    potential_keys = db.query(ApiKey).filter(
        ApiKey.key_prefix == prefix,
        ApiKey.is_active,
    ).all()
    for db_key in potential_keys:
        input_hash = hashlib.sha256(api_key.encode()).hexdigest()
        # Constant-time comparison to prevent timing attacks.
        if secrets.compare_digest(input_hash, db_key.key_hash):
            # FP-11: reject an expired key (tz-aware; compare in UTC).
            if db_key.expires_at is not None and db_key.expires_at < datetime.now(
                timezone.utc
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key has expired",
                )
            db_key.last_used_at = datetime.utcnow()
            db.commit()
            request.state.api_key_scope = db_key.scope or "full"
            return db_key.user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )


def _authenticate_jwt(request: Request, db: Session, token: str) -> models.User:
    """Decode an OAuth2 bearer and return its user (records full scope). Raises
    403 on a bad/undecodable token, 404 on an unknown subject. Does NOT check
    ``user_type`` or ``is_active`` — callers layer those (operator endpoints
    reject customers; read endpoints require active)."""
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
    request.state.api_key_scope = "full"
    return user


def get_current_user_with_api_key(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2_optional),
    api_key: str = Depends(api_key_header),
) -> models.User:
    """Authenticate STAFF (admin/employee JWT) OR the storefront BFF (service
    X-API-Key); the key takes precedence. Records the caller's effective scope on
    ``request.state.api_key_scope`` so ``require_write_scope`` can gate writes.

    A CUSTOMER session JWT is **rejected (403)** — every endpoint behind this is an
    operator/service surface (order-create, returns record/transition, inventory
    reservations, category writes, …). Customer self-service uses
    ``get_current_customer``. Without this guard a customer token would satisfy
    ``require_write_scope`` and could, e.g., self-transition its own return to
    ``refunded`` (crediting stock + stamping a refund with no real money movement).
    """
    user = _authenticate_api_key(request, db, api_key)
    if user is not None:
        return user
    if token:
        user = _authenticate_jwt(request, db, token)
        if getattr(user, "user_type", None) == "customer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this endpoint",
            )
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_user_or_api_key_read(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2_optional),
    api_key: str = Depends(api_key_header),
) -> models.User:
    """READ-only auth for endpoints reached by BOTH the storefront BFF
    (``X-API-Key``, server-to-server — e.g. the refund flow's order read) AND
    authenticated users **including customers** (their own order-history detail).

    Unlike :func:`get_current_user_with_api_key`, this ALLOWS a customer JWT — it
    is a read, and the data is exactly what a customer already obtains via
    ``get_current_active_user``; the F1 customer-reject is write-scoped and
    unaffected (this dependency must never gate a write — it records full scope
    only so the api-key path keeps working, and writes are gated separately by
    ``require_write_scope`` on their own endpoints). Inactive JWT users are
    rejected, mirroring ``get_current_active_user``.
    """
    user = _authenticate_api_key(request, db, api_key)
    if user is not None:
        return user
    if token:
        user = _authenticate_jwt(request, db, token)
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return user
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