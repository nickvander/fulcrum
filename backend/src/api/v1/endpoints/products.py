import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from datetime import datetime

from src.api import dependencies
from src.api.dependencies import get_db, get_ai_service
from src.crud import crud_product, crud_product_image, crud_custom_field
from src.models.user import User
from src.schemas import product as product_schema, inventory as inventory_schema
from src.services.base import AIService
from src.tasks import generate_product_embedding

router = APIRouter()


@router.get("", response_model=product_schema.PaginatedProducts)
def read_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    sku: str = None,
    q: str = None,
):
    """
    Retrieve products.
    """
    if sku:
        products = crud_product.product.get_by_sku(db, sku=sku)
        if not products:
            raise HTTPException(status_code=404, detail="Product not found")
        # Wrap single product in paginated response
        return {
            "data": [products],
            "currentPage": 1,
            "totalPages": 1,
            "totalItems": 1,
            "pageSize": 1,
            "hasNextPage": False,
            "hasPrevPage": False
        }
    
    filters = {}
    if q:
        filters['search_term'] = q
        
    products = crud_product.product.get_multi_paginated(db, skip=skip, limit=limit, filters=filters)
    return products


@router.post("", response_model=product_schema.Product)
def create_product(
    *,
    db: Session = Depends(get_db),
    product_in: product_schema.ProductCreate,
):
    """
    Create new product.
    """
    product = crud_product.product.get_by_sku(db, sku=product_in.sku)
    if product:
        raise HTTPException(
            status_code=409,
            detail="A product with this SKU already exists.",
        )
    product = crud_product.product.create(db, obj_in=product_in)
    
    # Try to generate embedding, but don't fail product creation if it fails
    try:
        generate_product_embedding.delay(product.id)
    except Exception as e:
        # Log the error but don't block product creation
        print(f"Warning: Failed to queue embedding generation: {e}")
    
    return product


@router.put("/{product_id}", response_model=product_schema.Product)
def update_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    product_in: product_schema.ProductUpdate,
):
    """
    Update a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    product = crud_product.product.update(db, db_obj=product, obj_in=product_in)
    generate_product_embedding.delay(product.id)
    return product


@router.get("/{product_id}", response_model=product_schema.Product)
def read_product(*, db: Session = Depends(get_db), product_id: int):
    """
    Get product by ID.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    return product


@router.delete("/{product_id}", response_model=product_schema.Product)
def delete_product(*, db: Session = Depends(get_db), product_id: int):
    """
    Delete a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    product = crud_product.product.remove(db, id=product_id)
    return product


@router.delete("", response_model=Dict[str, Any])
def delete_multiple_products(
    *,
    db: Session = Depends(get_db),
    product_ids: List[int],
):
    """
    Delete multiple products.
    """
    deleted_count = 0
    for product_id in product_ids:
        product = crud_product.product.get(db, id=product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with id {product_id} not found",
            )
        crud_product.product.remove(db, id=product_id)
        deleted_count += 1
    
    return {
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} products"
    }


@router.post("/{product_id}/images", response_model=product_schema.ProductImage)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a product image.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Ensure the upload directory exists
    upload_dir = "uploads/product_images"
    os.makedirs(upload_dir, exist_ok=True)

    # Save the file
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Create the product image record
    image_in = product_schema.ProductImageCreate(
        product_id=product_id, image_path=file.filename
    )
    image = crud_product_image.product_image.create(db, obj_in=image_in)
    return image


@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a product image.
    """
    image = crud_product_image.product_image.get(db=db, id=image_id)
    if not image or image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product image not found")
    
    # Delete the actual file from storage
    if image.image_path and os.path.exists(image.image_path):
        os.remove(image.image_path)
    
    crud_product_image.product_image.remove(db=db, id=image_id)
    return Response(status_code=204)

@router.put("/{product_id}/images/{image_id}", response_model=product_schema.ProductImage)
def update_product_image(
    product_id: int,
    image_id: int,
    image_update: product_schema.ProductImageUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a product image's details (title, description).
    """
    db_image = crud_product_image.product_image.get(db=db, id=image_id)
    if not db_image or db_image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product image not found")
    
    updated_image = crud_product_image.product_image.update(
        db=db, db_obj=db_image, obj_in=image_update
    )
    return updated_image


@router.post(
    "/{product_id}/images/{image_id}/set-primary",
    response_model=product_schema.ProductImage
)
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Set a product image as the primary image.
    """
    image = crud_product_image.product_image.set_primary_image(
        db=db, product_id=product_id, image_id=image_id
    )
    if not image:
        raise HTTPException(status_code=404, detail="Product image not found")
    return image


@router.post("/search", response_model=List[product_schema.Product])
def search_products(
    query: str,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Search for products using a semantic query.
    """
    embedding = ai_service.generate_embedding(query)
    products = crud_product.product.get_similar(db, embedding=embedding)
    return products


@router.post("/{product_id}/adjust-stock", response_model=product_schema.Product)
def adjust_stock(
    product_id: int,
    stock_adjustment: inventory_schema.StockAdjustment,
    current_user: User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adjust the stock level for a product.
    """
    from src.services.inventory_service import inventory_service
    
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Use centralized service
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=stock_adjustment.adjustment,
        reason=stock_adjustment.reason,
        location=getattr(stock_adjustment, 'location', 'default'),
        user_id=current_user.email if current_user.email else f"user_{current_user.id}"
    )
    
    db.commit()
    
    # Explicitly query the product with its inventory items and adjustments to ensure fresh data is returned
    from sqlalchemy.orm import joinedload
    from src.models.product import Product
    
    # Re-query the product with its inventory items and adjustments to ensure fresh data is returned
    refreshed_product = db.query(Product)\
        .options(joinedload(Product.inventory_items))\
        .options(joinedload(Product.inventory_adjustments))\
        .filter(Product.id == product_id).first()
    
    if not refreshed_product:
        raise HTTPException(status_code=404, detail="Product not found after adjustment")
    
    return refreshed_product


@router.post("/{product_id}/custom-fields")
def save_product_custom_fields(
    product_id: int,
    custom_fields: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Save custom field values for a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud_custom_field.product_custom_field.save_for_product(
        db=db, product_id=product_id, custom_fields_in=custom_fields
    )
    return {"message": "Custom fields saved successfully"}

