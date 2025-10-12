from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.crud import crud_custom_field
from src.schemas import custom_field as custom_field_schema

router = APIRouter()

@router.get("", response_model=List[custom_field_schema.CustomField])
def read_custom_fields(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve custom fields.
    """
    custom_fields = crud_custom_field.custom_field.get_multi(db, skip=skip, limit=limit)
    return custom_fields

@router.post("", response_model=custom_field_schema.CustomField)
def create_custom_field(
    *,
    db: Session = Depends(get_db),
    custom_field_in: custom_field_schema.CustomFieldCreate,
):
    """
    Create new custom field.
    """
    custom_field = crud_custom_field.custom_field.create(db, obj_in=custom_field_in)
    return custom_field
