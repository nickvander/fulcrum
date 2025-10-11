from fastapi import APIRouter

from src.api.v1.endpoints import (
    products,
    suppliers,
    users,
    marketplace,
    uploads,
    ai,
)
from src.api import custom_fields

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(
    suppliers.router, prefix="/suppliers", tags=["suppliers"]
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    marketplace.router, prefix="/marketplace", tags=["marketplace"]
)
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(
    custom_fields.router, prefix="/custom-fields", tags=["custom-fields"]
)
