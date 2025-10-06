from fastapi import APIRouter

from src.api.v1.endpoints import products, suppliers, users

api_router = APIRouter()
api_router.include_router(products.router)
api_router.include_router(suppliers.router)
api_router.include_router(users.router)
