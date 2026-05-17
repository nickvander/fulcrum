"""
API endpoints for managing marketplaces.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict

from src.api import dependencies
from src.core.errors import LocalizedHTTPException
from src.models.user import User
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

@router.get("/listings/")
def read_marketplace_listings(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve all product listings across marketplaces.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing

    listings = (
        db.query(ModelListing)
        .options(joinedload(ModelListing.product))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": listing.id,
            "product_id": listing.product_id,
            "marketplace_id": listing.marketplace_id,
            "external_listing_id": listing.external_listing_id,
            "listing_url": listing.listing_url,
            "status": listing.status,
            "sync_status": listing.sync_status,
            "marketplace_price": listing.marketplace_price,
            "original_price": listing.original_price,
            "discount_percentage": listing.discount_percentage,
            "product_name": (
                listing.product.name
                if listing.product
                else f"Product #{listing.product_id}"
            ),
        }
        for listing in listings
    ]

@router.get("/{marketplace_id}/summary")
def read_marketplace_summary(
    marketplace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(dependencies.get_current_active_user),
):
    """
    Return per-marketplace operational summary for the connection card:
    - total listings, healthy count, issues count
    - most recent sync timestamp
    - credential connection state + token expiry
    """
    from datetime import datetime, timezone
    from sqlalchemy import func
    from src.models.marketplace import MarketplaceListing as ModelListing
    from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred

    db_marketplace = crud_marketplace.marketplace.get(db=db, id=marketplace_id)
    if db_marketplace is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.marketplaceNotFound",
            params={"id": marketplace_id},
            detail="Marketplace not found",
        )

    listings_q = db.query(ModelListing).filter(ModelListing.marketplace_id == marketplace_id)
    listing_count = listings_q.count()
    healthy_count = listings_q.filter(ModelListing.sync_status == "IN_SYNC").count()
    issues_count = (
        listings_q.filter(ModelListing.sync_status.in_(["FAILED", "ERROR", "SYNC_ERROR"])).count()
    )
    last_sync_at = (
        db.query(func.max(ModelListing.last_sync))
        .filter(ModelListing.marketplace_id == marketplace_id)
        .scalar()
    )

    credential = crud_cred.get_by_marketplace(
        db, user_id=current_user.id, marketplace_id=marketplace_id
    )
    token_expires_at = credential.expires_at if credential else None
    token_expires_in_days = None
    if token_expires_at is not None:
        delta = token_expires_at - datetime.now(token_expires_at.tzinfo or timezone.utc)
        token_expires_in_days = int(delta.total_seconds() // 86400)

    return {
        "marketplace_id": marketplace_id,
        "listing_count": listing_count,
        "healthy_count": healthy_count,
        "issues_count": issues_count,
        "last_sync_at": last_sync_at.isoformat() if last_sync_at else None,
        "credential_connected": credential is not None,
        "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
        "token_expires_in_days": token_expires_in_days,
    }


@router.get("/{marketplace_id}", response_model=marketplace_schema.Marketplace)
def read_marketplace(marketplace_id: int, db: Session = Depends(get_db)):
    db_marketplace = crud_marketplace.marketplace.get(db=db, id=marketplace_id)
    if db_marketplace is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplaceCredentials.marketplaceNotFound",
            params={"id": marketplace_id},
            detail="Marketplace not found",
        )
    return db_marketplace

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
    current_user: User = Depends(dependencies.get_current_active_user)
):
    """
    Trigger manual sync for a listing.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing
    
    listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
    if not listing:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplace.listingNotFound",
            params={"id": listing_id},
            detail="Listing not found",
        )

    # Get credentials for current user
    from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
    db_cred = crud_cred.get_by_marketplace(db, user_id=current_user.id, marketplace_id=listing.marketplace_id)
    if not db_cred:
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.marketplace.noCredentialsForMarketplace",
            params={"marketplaceId": listing.marketplace_id},
            detail="No credentials found for this marketplace",
        )
        
    from src.services.marketplace_service import marketplace_service
    token = await marketplace_service.get_valid_access_token(db, db_cred.id)
    
    # Trigger sync logic via service
    await marketplace_service.sync_product_inventory(
        db, 
        listing.marketplace.name, 
        listing.external_listing_id, 
        listing.product.total_stock,
        access_token=token
    )
    
    return listing

@router.post("/import", response_model=Dict[str, int])
async def import_marketplace_listings(
    *,
    db: Session = Depends(get_db),
    marketplace_id: int,
    current_user: User = Depends(dependencies.get_current_active_user)
):
    """
    Import all listings from a specific marketplace into Fulcrum.
    """
    from src.services.marketplace_listing_service import marketplace_listing_service
    try:
        return await marketplace_listing_service.import_marketplace_listings(db, marketplace_id, current_user.id)
    except ValueError as e:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplace.importFailed",
            params={"reason": str(e)},
            detail=str(e),
        )

@router.post("/publish", response_model=marketplace_schema.MarketplaceListing)
async def publish_to_marketplace(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    marketplace_id: int,
    current_user: User = Depends(dependencies.get_current_active_user)
):
    """
    Publish a Fulcrum product to a marketplace.
    """
    from src.services.marketplace_listing_service import marketplace_listing_service
    try:
        return await marketplace_listing_service.publish_to_marketplace(db, product_id, marketplace_id, current_user.id)
    except ValueError as e:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplace.publishFailed",
            params={"reason": str(e)},
            detail=str(e),
        )

@router.post("/listings/{listing_id}/map", response_model=marketplace_schema.MarketplaceListing)
async def map_listing_to_product(
    *,
    db: Session = Depends(get_db),
    listing_id: int,
    product_id: int,
):
    """
    Manually map a marketplace listing to a Fulcrum product.
    """
    from src.models.marketplace import MarketplaceListing as ModelListing
    listing = db.query(ModelListing).filter(ModelListing.id == listing_id).first()
    if not listing:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.marketplace.listingNotFound",
            params={"id": listing_id},
            detail="Listing not found",
        )

    listing.product_id = product_id
    listing.status = "SYNCED"
    db.commit()
    return listing
