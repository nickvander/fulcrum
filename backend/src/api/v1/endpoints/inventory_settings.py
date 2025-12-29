from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api import dependencies
from src.api.dependencies import get_db
from src.models.user import User
from src.schemas.store_settings import StoreSettings as StoreSettingsSchema, StoreSettingsUpdate
from src.schemas.product_inventory_settings import ProductInventorySettings as ProductInventorySettingsSchema, ProductInventorySettingsUpdate, ProductInventorySettingsCreate
from src.crud.crud_store_settings import store_settings as crud_store_settings
from src.crud.crud_product_inventory_settings import product_inventory_settings as crud_prod_settings

router = APIRouter()

@router.get("/store", response_model=StoreSettingsSchema)
def get_store_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Get global store settings. Creates default if not exists.
    """
    return crud_store_settings.get_settings(db)

@router.put("/store", response_model=StoreSettingsSchema)
def update_store_settings(
    settings_in: StoreSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Update global store settings.
    """
    settings = crud_store_settings.get_settings(db)
    return crud_store_settings.update(db, db_obj=settings, obj_in=settings_in)

@router.get("/product/{product_id}", response_model=ProductInventorySettingsSchema)
def get_product_inventory_settings(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Get inventory settings for a specific product.
    """
    settings = crud_prod_settings.get_by_product(db, product_id=product_id)
    if not settings:
        # Return default structure or 404? 
        # Better to return empty overrides or 404. 
        # Frontend handles "no override".
        # Let's return a default object with null overrides if not found, to simplify frontend.
        # Check if product exists first? Assuming yes.
        return {"product_id": product_id, "low_inventory_days_threshold": None, "id": 0} # Hacky defaults
    return settings

@router.put("/product/{product_id}", response_model=ProductInventorySettingsSchema)
def update_product_inventory_settings(
    product_id: int,
    settings_in: ProductInventorySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user)
) -> Any:
    """
    Update/Create inventory settings for a specific product.
    """
    settings = crud_prod_settings.get_by_product(db, product_id=product_id)
    if settings:
        return crud_prod_settings.update(db, db_obj=settings, obj_in=settings_in)
    else:
        create_in = ProductInventorySettingsCreate(
            product_id=product_id,
            low_inventory_days_threshold=settings_in.low_inventory_days_threshold
        )
        return crud_prod_settings.create(db, obj_in=create_in)
