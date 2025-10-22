from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from src.api.v1.api import api_router
from src.database import SessionLocal
from src.crud import crud_user
from src.schemas.user import UserCreate
from src.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = SessionLocal()
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
    finally:
        db.close()
    yield
    # Shutdown

app = FastAPI(title="Fulcrum API", lifespan=lifespan)

# Mount the uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
