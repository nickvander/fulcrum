"""
API endpoints for managing products.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

from ..schemas import product as product_schema, inventory as inventory_schema, custom_field as custom_field_schema
from ..schemas.pagination import PaginatedProductsResponse
from ..schemas.product_variant import ProductVariant as ProductVariantSchema, ProductVariantCreate, ProductVariantUpdate
from ..database import get_db
from ..tasks import generate_product_embedding
from ..crud import crud_product, crud_custom_field, crud_product_image, crud_product_variant
from ..models.inventory import InventoryItem, InventoryAdjustment
from ..models.product_variant import ProductVariant

router = APIRouter()

@router.post("/{product_id}/custom-fields", response_model=custom_field_schema.ProductCustomField)
def create_product_custom_field(
    product_id: int,
    custom_field: custom_field_schema.ProductCustomFieldCreate,
    db: Session = Depends(get_db),
):
    custom_field.product_id = product_id
    return crud_custom_field.product_custom_field.create(db=db, obj_in=custom_field)

@router.get("/{product_id}/custom-fields", response_model=List[custom_field_schema.ProductCustomField])
def read_product_custom_fields(
    product_id: int,
    db: Session = Depends(get_db),
):
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product.custom_fields

@router.put("/custom-fields/{custom_field_id}", response_model=custom_field_schema.ProductCustomField)
def update_product_custom_field(
    custom_field_id: int,
    custom_field: custom_field_schema.ProductCustomFieldUpdate,
    db: Session = Depends(get_db),
):
    db_custom_field = crud_custom_field.product_custom_field.get(db=db, id=custom_field_id)
    if not db_custom_field:
        raise HTTPException(status_code=404, detail="Product custom field not found")
    return crud_custom_field.product_custom_field.update(db=db, db_obj=db_custom_field, obj_in=custom_field)

@router.delete("/custom-fields/{custom_field_id}", response_model=custom_field_schema.ProductCustomField)
def delete_product_custom_field(
    custom_field_id: int, db: Session = Depends(get_db)
):
    db_custom_field = crud_custom_field.product_custom_field.get(db=db, id=custom_field_id)
    if not db_custom_field:
        raise HTTPException(status_code=404, detail="Product custom field not found")
    return crud_custom_field.product_custom_field.remove(db=db, id=custom_field_id)


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

@router.post("/{product_id}/adjust-stock", response_model=product_schema.Product)
def adjust_stock(
    product_id: int,
    stock_adjustment: inventory_schema.StockAdjustment,
    db: Session = Depends(get_db),
):
    """
    Adjust the stock of a product.
    """
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create an inventory adjustment record for audit trail
    inventory_adjustment = InventoryAdjustment(
        product_id=product_id,
        adjustment=stock_adjustment.adjustment,
        reason=stock_adjustment.reason,
        # In a real implementation, you would get the current user from the request
        # For now, we'll set a placeholder value
        created_by="system"  
    )
    db.add(inventory_adjustment)
    db.commit()
    
    # Create or update inventory item to reflect the new quantity
    # For this implementation, we'll create a new inventory item with the adjustment
    inventory_item = InventoryItem(
        product_id=product_id,
        quantity=stock_adjustment.adjustment,  # Only the adjustment amount
        location=getattr(stock_adjustment, 'location', None)  # If location is provided
    )
    db.add(inventory_item)
    db.commit()
    
    # Refresh the product to get the updated data
    db.refresh(db_product)
    return db_product


@router.get("/", response_model=PaginatedProductsResponse)
def read_products(
    skip: int = 0, 
    limit: int = 10, 
    category: str = None,
    brand: str = None,
    min_price: float = None,
    max_price: float = None,
    search_term: str = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of products with pagination and optional filtering.
    """
    # Build filters dictionary
    filters = {}
    if category:
        filters['category'] = category
    if brand:
        filters['brand'] = brand
    if min_price is not None:
        filters['min_price'] = min_price
    if max_price is not None:
        filters['max_price'] = max_price
    if search_term:
        filters['search_term'] = search_term
    
    result = crud_product.product.get_multi_paginated(db, skip=skip, limit=limit, filters=filters)
    return result

@router.get("/{product_id}", response_model=product_schema.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single product by its ID.
    """
    db_product = crud_product.product.get(db=db, id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.delete("/{product_id}", response_model=product_schema.Product)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product by its ID.
    """
    # Get product before deletion to return its data
    db_product = crud_product.product.get(db=db, id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete the product
    crud_product.product.remove(db=db, id=product_id)
    
    # Return original product data since the deleted object may be detached
    return db_product


@router.delete("/", response_model=None)
def delete_multiple_products(ids: List[int] = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Delete multiple products by their IDs.
    """
    deleted_products = []
    for product_id in ids:
        db_product = crud_product.product.get(db=db, id=product_id)
        if db_product is None:
            raise HTTPException(status_code=404, detail=f"Product with id {product_id} not found")
        deleted_product = crud_product.product.remove(db=db, id=product_id)
        deleted_products.append(deleted_product)
    
    return {"message": f"Successfully deleted {len(deleted_products)} products", "deleted_count": len(deleted_products)}

@router.get("/search/", response_model=PaginatedProductsResponse)
def search_products(
    q: str, 
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(get_db)
):
    """
    Perform a semantic search for products with pagination.
    """
    filters = {'search_term': q}
    result = crud_product.product.get_multi_paginated(db, skip=skip, limit=limit, filters=filters)
    return result

@router.get("/search/advanced", response_model=PaginatedProductsResponse)
def search_products_advanced(
    skip: int = 0, 
    limit: int = 10,
    category: str = None,
    brand: str = None,
    min_price: float = None,
    max_price: float = None,
    min_stock: int = None,
    max_stock: int = None,
    search_term: str = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    db: Session = Depends(get_db)
):
    """
    Perform an advanced search for products with multiple filters and sorting.
    """
    filters = {}
    if category:
        filters['category'] = category
    if brand:
        filters['brand'] = brand
    if min_price is not None:
        filters['min_price'] = min_price
    if max_price is not None:
        filters['max_price'] = max_price
    if search_term:
        filters['search_term'] = search_term
    
    result = crud_product.product.get_multi_paginated(db, skip=skip, limit=limit, filters=filters)
    
    # Apply sorting if needed (could be enhanced in the future)
    # For now, we'll just return the result as is
    return result


@router.post("/products/{product_id}/images", response_model=product_schema.ProductImage)
def create_product_image(
    product_id: int,
    image: product_schema.ProductImageCreate,
    db: Session = Depends(get_db),
):
    return crud_product_image.product_image.create(db=db, obj_in=image)

@router.put("/products/{product_id}/images/{image_id}", response_model=product_schema.ProductImage)
def update_product_image(
    product_id: int,
    image_id: int,
    image_in: product_schema.ProductImageUpdate,
    db: Session = Depends(get_db),
):
    db_image = crud_product_image.product_image.get(db=db, id=image_id)
    if not db_image or db_image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Image not found")
    return crud_product_image.product_image.update(db=db, db_obj=db_image, obj_in=image_in)


@router.delete("/products/{product_id}/images/{image_id}", response_model=product_schema.ProductImage)
def delete_product_image(
    product_id: int, image_id: int, db: Session = Depends(get_db)
):
    db_image = crud_product_image.product_image.get(db=db, id=image_id)
    if not db_image or db_image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Image not found")
    return crud_product_image.product_image.remove(db=db, id=image_id)


# Product Variant Endpoints
@router.post("/products/{product_id}/variants", response_model=ProductVariantSchema)
def create_product_variant(
    product_id: int, 
    variant: ProductVariantCreate, 
    db: Session = Depends(get_db)
):
    """Create a new variant for a product."""
    # Verify the product exists
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if SKU already exists
    existing_variant = crud_product_variant.product_variant.get_by_sku(db, sku=variant.sku)
    if existing_variant:
        raise HTTPException(status_code=409, detail="Variant with this SKU already exists.")
    
    # Set the product_id from the URL parameter to ensure consistency
    variant_in = variant.model_copy(update={"product_id": product_id})
    db_variant = crud_product_variant.product_variant.create(db=db, obj_in=variant_in)
    return db_variant


@router.get("/products/{product_id}/variants", response_model=List[ProductVariantSchema])
def read_product_variants(
    product_id: int, 
    db: Session = Depends(get_db)
):
    """Get all variants for a specific product."""
    # Verify the product exists
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    variants = crud_product_variant.product_variant.get_by_product_id(db, product_id=product_id)
    return variants


@router.get("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
def read_product_variant(
    product_id: int, 
    variant_id: int, 
    db: Session = Depends(get_db)
):
    """Get a specific variant for a product."""
    # Verify the product exists
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get the specific variant
    db_variant = crud_product_variant.product_variant.get(db=db, id=variant_id)
    if not db_variant or db_variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product variant not found")
    
    return db_variant


@router.put("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
def update_product_variant(
    product_id: int, 
    variant_id: int, 
    variant_update: ProductVariantUpdate, 
    db: Session = Depends(get_db)
):
    """Update a specific product variant."""
    # Verify the product exists
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get the specific variant
    db_variant = crud_product_variant.product_variant.get(db=db, id=variant_id)
    if not db_variant or db_variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product variant not found")
    
    # Check if the new SKU would conflict with another variant (excluding this one)
    if variant_update.sku and variant_update.sku != db_variant.sku:
        existing_variant = crud_product_variant.product_variant.get_by_sku(db, sku=variant_update.sku)
        if existing_variant and existing_variant.id != variant_id:
            raise HTTPException(status_code=409, detail="Variant with this SKU already exists.")
    
    # Update the variant
    updated_variant = crud_product_variant.product_variant.update(
        db=db, 
        db_obj=db_variant, 
        obj_in=variant_update
    )
    return updated_variant


@router.delete("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
def delete_product_variant(
    product_id: int, 
    variant_id: int, 
    db: Session = Depends(get_db)
):
    """Delete a specific product variant."""
    # Verify the product exists
    db_product = crud_product.product.get(db=db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get the specific variant
    db_variant = crud_product_variant.product_variant.get(db=db, id=variant_id)
    if not db_variant or db_variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product variant not found")
    
    # Delete the variant
    deleted_variant = crud_product_variant.product_variant.remove(db=db, id=variant_id)
    return deleted_variant
