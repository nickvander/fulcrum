from pydantic import BaseModel
from typing import List, Optional
from ..schemas.product import Product

class PaginatedProductsResponse(BaseModel):
    data: List[Product]
    currentPage: int
    totalPages: int
    totalItems: int
    pageSize: int
    hasNextPage: bool
    hasPrevPage: bool