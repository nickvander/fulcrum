"""
API endpoints for managing suppliers.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.schemas import supplier as supplier_schema
from src.database import get_db
from src.crud import crud_supplier

router = APIRouter()

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

@router.get("/{supplier_id}", response_model=supplier_schema.Supplier)
def read_supplier(*, db: Session = Depends(get_db), supplier_id: int):
    """
    Get supplier by ID.
    """
    supplier = crud_supplier.supplier.get(db, id=supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="The supplier with this ID does not exist in the system.",
        )
    return supplier

@router.put("/{supplier_id}", response_model=supplier_schema.Supplier)
def update_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    supplier_in: supplier_schema.SupplierUpdate,
):
    """
    Update a supplier.
    """
    supplier = crud_supplier.supplier.get(db, id=supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="The supplier with this ID does not exist in the system.",
        )
    supplier = crud_supplier.supplier.update(db, db_obj=supplier, obj_in=supplier_in)
    return supplier

@router.delete("/{supplier_id}", response_model=supplier_schema.Supplier)
def delete_supplier(*, db: Session = Depends(get_db), supplier_id: int):
    """
    Delete a supplier.
    """
    supplier = crud_supplier.supplier.get(db, id=supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="The supplier with this ID does not exist in the system.",
        )
    supplier = crud_supplier.supplier.remove(db, id=supplier_id)
    return supplier
