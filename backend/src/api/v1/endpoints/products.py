"""
API endpoints for managing products.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import shutil

from src.schemas import product as product_schema
from src.database import get_db
from src.crud import crud_product, crud_product_image
from src.tasks import generate_product_embedding
from src.api.dependencies import get_ai_service
from src.services.base import AIService

router = APIRouter()

# Directory to store product images
UPLOADS_DIR = Path("uploads/product_images")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

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

@router.post("/{product_id}/images", response_model=product_schema.ProductImage)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an image for a specific product.
    """
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create a subdirectory for the product if it doesn't exist
    product_image_dir = UPLOADS_DIR / str(product_id)
    product_image_dir.mkdir(exist_ok=True)

    # Secure the filename and save the file
    if ".." in file.filename or "/" in file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    
    file_path = product_image_dir / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create the database record
    image_in = product_schema.ProductImageCreate(
        product_id=product_id,
        image_path=str(file_path)
    )
    db_image = crud_product_image.product_image.create(db=db, obj_in=image_in)
    return db_image

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
def search_products(
    q: str,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Perform a semantic search for products.
    """
    embedding = ai_service.generate_embedding(q)
    products = crud_product.product.search(db, embedding=embedding, limit=10)
    return products

@router.put("/{product_id}", response_model=product_schema.Product)
def update_product(
    product_id: int,
    product_in: product_schema.ProductUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a product and trigger a background task to re-generate its embedding.
    """
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = crud_product.product.update(
        db=db, db_obj=db_product, obj_in=product_in
    )
    generate_product_embedding.delay(updated_product.id)
    return updated_product
