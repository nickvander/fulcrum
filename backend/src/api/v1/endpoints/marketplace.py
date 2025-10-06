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
