
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import custom_field as custom_field_schema
from ..database import get_db
from ..crud import crud_custom_field

router = APIRouter()

@router.post("/", response_model=custom_field_schema.CustomField)
def create_custom_field(
    custom_field: custom_field_schema.CustomFieldCreate, db: Session = Depends(get_db)
):
    return crud_custom_field.custom_field.create(db=db, obj_in=custom_field)

@router.get("/", response_model=List[custom_field_schema.CustomField])
def read_custom_fields(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return crud_custom_field.custom_field.get_multi(db, skip=skip, limit=limit)

@router.put("/{custom_field_id}", response_model=custom_field_schema.CustomField)
def update_custom_field(
    custom_field_id: int,
    custom_field: custom_field_schema.CustomFieldUpdate,
    db: Session = Depends(get_db),
):
    db_custom_field = crud_custom_field.custom_field.get(db=db, id=custom_field_id)
    if not db_custom_field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    return crud_custom_field.custom_field.update(db=db, db_obj=db_custom_field, obj_in=custom_field)

@router.delete("/{custom_field_id}", response_model=custom_field_schema.CustomField)
def delete_custom_field(
    custom_field_id: int, db: Session = Depends(get_db)
):
    db_custom_field = crud_custom_field.custom_field.get(db=db, id=custom_field_id)
    if not db_custom_field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    return crud_custom_field.custom_field.remove(db=db, id=custom_field_id)

