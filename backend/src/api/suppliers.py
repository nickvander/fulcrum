"""
API endpoints for managing suppliers.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import supplier as supplier_schema
from ..models import supplier as supplier_model
from ..database import get_db

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
)

@router.post("/", response_model=supplier_schema.Supplier)
def create_supplier(supplier: supplier_schema.SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = supplier_model.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.get("/", response_model=List[supplier_schema.Supplier])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    suppliers = db.query(supplier_model.Supplier).offset(skip).limit(limit).all()
    return suppliers
