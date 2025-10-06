"""
API endpoints for managing products.

This router provides CRUD (Create, Read, Update, Delete) operations for products.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import product as product_schema
from ..models import product as product_model
from ..database import get_db
from ..tasks import generate_product_embedding

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

@router.post("/", response_model=product_schema.Product)
def create_product(product: product_schema.ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product and trigger a background task to generate its embedding.

    Args:
        product: The product data to create, based on the ProductCreate schema.
        db: The database session, injected by FastAPI.

    Returns:
        The newly created product, including its database ID.
    """
    db_product = product_model.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Trigger the background task to generate the embedding
    generate_product_embedding.delay(db_product.id)

    return db_product

@router.get("/", response_model=List[product_schema.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of products with pagination.

    Args:
        skip: The number of products to skip from the beginning.
        limit: The maximum number of products to return.
        db: The database session, injected by FastAPI.

    Returns:
        A list of product objects.
    """
    products = db.query(product_model.Product).offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=product_schema.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single product by its ID.

    Args:
        product_id: The ID of the product to retrieve.
        db: The database session, injected by FastAPI.

    Raises:
        HTTPException: If a product with the given ID is not found.

    Returns:
        The product object.
    """
    db_product = db.query(product_model.Product).filter(product_model.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.get("/search/", response_model=List[product_schema.Product])
def search_products(q: str, db: Session = Depends(get_db)):
    """
    Perform a semantic search for products.

    NOTE: This is a placeholder implementation. The actual vector search
    is blocked by the database migration issue. This endpoint currently
    returns the first 10 products.

    Args:
        q: The search query string.
        db: The database session, injected by FastAPI.

    Returns:
        A list of products that are semantically similar to the query.
    """
    # Placeholder: In a real implementation, you would generate an embedding
    # for the query 'q' and use it to perform a similarity search in the DB.
    # Example: db.query(models.Product).order_by(models.Product.embedding.l2_distance(query_embedding)).limit(10).all()
    print(f"Search query: {q}")
    
    # Return the first 10 products as a placeholder
    products = db.query(product_model.Product).limit(10).all()
    return products
