from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.crud import crud_purchase_order
from src.schemas import purchase_order as po_schema
from src.services.purchase_order_service import purchase_order_service

router = APIRouter()

@router.post("/", response_model=po_schema.PurchaseOrder)
def create_purchase_order(
    *,
    db: Session = Depends(get_db),
    po_in: po_schema.PurchaseOrderCreate,
) -> Any:
    """
    Create a new Purchase Order.
    """
    po = crud_purchase_order.purchase_order.create_with_items(db=db, obj_in=po_in)
    return po

@router.get("/", response_model=List[po_schema.PurchaseOrder])
def read_purchase_orders(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve Purchase Orders.
    """
    return crud_purchase_order.purchase_order.get_multi(db, skip=skip, limit=limit)

@router.get("/{id}", response_model=po_schema.PurchaseOrder)
def read_purchase_order(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get Purchase Order by ID.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return po

@router.put("/{id}", response_model=po_schema.PurchaseOrder)
def update_purchase_order(
    *,
    db: Session = Depends(get_db),
    id: int,
    po_in: po_schema.PurchaseOrderUpdate,
) -> Any:
    """
    Update a Purchase Order.
    """
    po = crud_purchase_order.purchase_order.get(db=db, id=id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    po = crud_purchase_order.purchase_order.update(db=db, db_obj=po, obj_in=po_in)
    return po

@router.post("/{id}/status", response_model=po_schema.PurchaseOrder)
def transition_status(
    *,
    db: Session = Depends(get_db),
    id: int,
    status: po_schema.PurchaseOrderStatus,
):
    """
    Transition Purchase Order status.
    """
    try:
        po = purchase_order_service.transition_status(db=db, po_id=id, new_status=status)
        return po
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/receive", response_model=po_schema.PurchaseOrder)
def receive_items(
    *,
    db: Session = Depends(get_db),
    id: int,
    received_items: List[dict],  # Ideally define a schema for this
):
    """
    Receive items for a Purchase Order.
    Body: List of { "product_id": int, "quantity": int }
    """
    try:
        po = purchase_order_service.receive_items(db=db, po_id=id, received_items=received_items)
        return po
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
