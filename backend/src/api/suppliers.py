"""
API endpoints for managing suppliers.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..schemas import supplier as supplier_schema
from ..database import get_db
from ..crud import crud_supplier

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
)

@router.post("/", response_model=supplier_schema.Supplier)
def create_supplier(
    supplier: supplier_schema.SupplierCreate, db: Session = Depends(get_db)
):
    return crud_supplier.supplier.create(db=db, obj_in=supplier)

@router.get("/", response_model=List[supplier_schema.Supplier])
def read_suppliers(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud_supplier.supplier.get_multi(db, skip=skip, limit=limit)
