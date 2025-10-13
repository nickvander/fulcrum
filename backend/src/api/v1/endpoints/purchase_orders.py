"""
API endpoints for managing purchase orders.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.schemas import purchase_order as purchase_order_schema
from src.database import get_db
from src.crud import crud_purchase_order

router = APIRouter()

@router.post("/", response_model=purchase_order_schema.PurchaseOrder)
def create_purchase_order(
    purchase_order: purchase_order_schema.PurchaseOrderCreate, db: Session = Depends(get_db)
):
    return crud_purchase_order.purchase_order.create(db=db, obj_in=purchase_order)

@router.get("/", response_model=List[purchase_order_schema.PurchaseOrder])
def read_purchase_orders(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud_purchase_order.purchase_order.get_multi(db, skip=skip, limit=limit)

@router.get("/{purchase_order_id}", response_model=purchase_order_schema.PurchaseOrder)
def read_purchase_order(*, db: Session = Depends(get_db), purchase_order_id: int):
    """
    Get purchase order by ID.
    """
    purchase_order = crud_purchase_order.purchase_order.get(db, id=purchase_order_id)
    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="The purchase order with this ID does not exist in the system.",
        )
    return purchase_order

@router.put("/{purchase_order_id}", response_model=purchase_order_schema.PurchaseOrder)
def update_purchase_order(
    *,
    db: Session = Depends(get_db),
    purchase_order_id: int,
    purchase_order_in: purchase_order_schema.PurchaseOrderUpdate,
):
    """
    Update a purchase order.
    """
    purchase_order = crud_purchase_order.purchase_order.get(db, id=purchase_order_id)
    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="The purchase order with this ID does not exist in the system.",
        )
    purchase_order = crud_purchase_order.purchase_order.update(db, db_obj=purchase_order, obj_in=purchase_order_in)
    return purchase_order

@router.delete("/{purchase_order_id}", response_model=purchase_order_schema.PurchaseOrder)
def delete_purchase_order(*, db: Session = Depends(get_db), purchase_order_id: int):
    """
    Delete a purchase order.
    """
    purchase_order = crud_purchase_order.purchase_order.get(db, id=purchase_order_id)
    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="The purchase order with this ID does not exist in the system.",
        )
    purchase_order = crud_purchase_order.purchase_order.remove(db, id=purchase_order_id)
    return purchase_order
