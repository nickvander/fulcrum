from fastapi import APIRouter

from src.api.v1.endpoints import products, suppliers, users, marketplace

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(marketplace.router, prefix="/marketplaces", tags=["marketplaces"])
