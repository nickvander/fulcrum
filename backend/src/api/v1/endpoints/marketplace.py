"""
API endpoints for managing marketplaces.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.schemas import marketplace as marketplace_schema
from src.database import get_db
from src.crud import crud_marketplace

router = APIRouter()

@router.post("/", response_model=marketplace_schema.Marketplace)
def create_marketplace(
    marketplace: marketplace_schema.MarketplaceCreate, db: Session = Depends(get_db)
):
    return crud_marketplace.marketplace.create(db=db, obj_in=marketplace)

@router.get("/", response_model=List[marketplace_schema.Marketplace])
def read_marketplaces(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud_marketplace.marketplace.get_multi(db, skip=skip, limit=limit)

@router.get("/{marketplace_id}", response_model=marketplace_schema.Marketplace)
def read_marketplace(marketplace_id: int, db: Session = Depends(get_db)):
    db_marketplace = crud_marketplace.marketplace.get(db=db, id=marketplace_id)
    if db_marketplace is None:
        raise HTTPException(status_code=404, detail="Marketplace not found")
    return db_marketplace

@router.get("/listings/", response_model=List[marketplace_schema.MarketplaceListing])
def read_marketplace_listings(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve all product listings across marketplaces.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing
    listings = db.query(ModelListing).offset(skip).limit(limit).all()
    return listings

@router.post("/listings/", response_model=marketplace_schema.MarketplaceListing)
async def create_marketplace_listing(
    *,
    db: Session = Depends(get_db),
    listing_in: marketplace_schema.MarketplaceListingCreate,
):
    """
    Create a new marketplace listing.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing
    db_obj = ModelListing(**listing_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.post("/listings/{listing_id}/sync", response_model=marketplace_schema.MarketplaceListing)
async def sync_marketplace_listing(
    *,
    db: Session = Depends(get_db),
    listing_id: int,
):
    """
    Trigger manual sync for a listing.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing
    
    listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Trigger sync logic via service (stub for now)
    # await marketplace_service.sync_product_inventory(db, listing.marketplace.name, listing.external_listing_id, listing.product.total_stock)
    
    return listing
