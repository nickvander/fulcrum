"""
API endpoints for managing products.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import product as product_schema, inventory as inventory_schema, custom_field as custom_field_schema
from ..database import get_db
from ..tasks import generate_product_embedding
from ..crud import crud_product, crud_custom_field
from ..models.inventory import InventoryItem

router = APIRouter(
    prefix="/products",
    tags=["products"],
)

@router.post("/{product_id}/custom-fields", response_model=custom_field_schema.ProductCustomField)
def create_product_custom_field(
    product_id: int,
    custom_field: custom_field_schema.ProductCustomFieldCreate,
    db: Session = Depends(get_db),
):
    custom_field.product_id = product_id
    return crud_custom_field.product_custom_field.create(db=db, obj_in=custom_field)

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

    # For now, just create a new inventory item.
    # A more robust implementation would update existing items.
    inventory_item = InventoryItem(
        product_id=product_id,
        quantity=stock_adjustment.adjustment,
    )
    db.add(inventory_item)
    db.commit()
    db.refresh(db_product)
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
