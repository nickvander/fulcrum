from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from src.api.v1.api import api_router
from src.database import SessionLocal
from src.crud import crud_user
from src.schemas.user import UserCreate
from src.config import settings
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.core.ratelimit import limiter
from src.core.errors import LocalizedHTTPException, localized_http_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Skip default superuser creation during test runs
    if os.getenv("TESTING") != "1":
        db = SessionLocal()
        try:
            # Try to create default superuser, but don't fail if table doesn't exist yet
            try:
                user = crud_user.user.get_by_email(db, email=settings.FIRST_SUPERUSER_EMAIL)
                if not user:
                    user_in = UserCreate(
                        email=settings.FIRST_SUPERUSER_EMAIL,
                        password=settings.FIRST_SUPERUSER_PASSWORD,
                        is_superuser=True,
                        user_type="admin",  # Set user_type to admin for superusers
                    )
                    crud_user.user.create(db, obj_in=user_in)
                    db.commit()
            except Exception as e:
                # Table might not exist yet (e.g., during initial setup)
                print(f"Note: Could not create default superuser yet: {e}")
                db.rollback()
        finally:
            db.close()
    yield
    # Shutdown

app = FastAPI(title="Fulcrum API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(LocalizedHTTPException, localized_http_exception_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: fastapi.tiangolo.com; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net;"
    return response

# Mount the uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
