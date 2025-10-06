"""
API endpoints for managing products.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import product as product_schema
from ..database import get_db
from ..tasks import generate_product_embedding
from ..crud import crud_product

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

@router.post("/", response_model=product_schema.Product)
def create_product(
    product: product_schema.ProductCreate, db: Session = Depends(get_db)
):
    """
    Create a new product and trigger a background task to generate its embedding.
    """
    db_product = crud_product.product.create(db=db, obj_in=product)
    generate_product_embedding.delay(db_product.id)
    return db_product

@router.get("/", response_model=List[product_schema.Product])
def read_products(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve a list of products with pagination.
    """
    products = crud_product.product.get_multi(db, skip=skip, limit=limit)
    return products

@router.get("/{product_id}", response_model=product_schema.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single product by its ID.
    """
    db_product = crud_product.product.get(db=db, id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.get("/search/", response_model=List[product_schema.Product])
def search_products(q: str, db: Session = Depends(get_db)):
    """
    Perform a semantic search for products. (Placeholder)
    """
    # This logic will be updated to use a specific search method in the CRUD class
    print(f"Search query: {q}")
    products = crud_product.product.get_multi(db, limit=10)
    return products
