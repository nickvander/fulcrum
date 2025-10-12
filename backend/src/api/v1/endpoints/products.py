import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_ai_service
from src.crud import crud_product, crud_product_image, crud_custom_field
from src.schemas import product as product_schema, inventory as inventory_schema
from src.services.ai_service import AIService
from src.tasks import generate_product_embedding

router = APIRouter()


@router.get("", response_model=List[product_schema.Product])
def read_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    sku: str = None,
):
    """
    Retrieve products.
    """
    if sku:
        products = crud_product.product.get_by_sku(db, sku=sku)
        if not products:
            raise HTTPException(status_code=404, detail="Product not found")
        return [products]
    products = crud_product.product.get_multi(db, skip=skip, limit=limit)
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
    generate_product_embedding.delay(product.id)
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
    
    # TODO: Delete the actual file from storage
    
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


@router.post("/{product_id}/adjust-stock")
def adjust_stock(
    product_id: int,
    stock_adjustment: inventory_schema.StockAdjustment,
    db: Session = Depends(get_db),
):
    """
    Adjust the stock level for a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # For simplicity, we'll assume one inventory item per product for now
    inventory_item = product.inventory_items[0] if product.inventory_items else None
    if not inventory_item:
        # Create one if it doesn't exist
        inventory_item = crud_product.inventory_item.create(
            db,
            obj_in={"product_id": product_id, "quantity": stock_adjustment.adjustment},
        )
    else:
        inventory_item.quantity += stock_adjustment.adjustment
        db.add(inventory_item)
        db.commit()
        db.refresh(inventory_item)

    return {"message": "Stock adjusted successfully", "new_quantity": inventory_item.quantity}


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

