"""
API endpoints for managing suppliers.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from src.schemas import supplier as supplier_schema
from src.schemas import supplier_product_alias as alias_schema
from src.schemas import supplier_product as supplier_product_schema
from src.database import get_db
from src.crud import crud_supplier, crud_supplier_product
from src.crud.crud_supplier_product_alias import supplier_product_alias as crud_supplier_product_alias

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
def read_supplier(
    supplier_id: int, db: Session = Depends(get_db)
):
    supplier = crud_supplier.supplier.get(db, id=supplier_id)
    if not supplier:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.get("/{supplier_id}/products", response_model=List[supplier_product_schema.SupplierProductWithDetails])
def read_supplier_products(
    supplier_id: int, db: Session = Depends(get_db)
):
    supplier_products = crud_supplier_product.supplier_product.get_by_supplier(db, supplier_id=supplier_id)
    result = []
    for sp in supplier_products:
        sp_dict = supplier_product_schema.SupplierProduct.model_validate(sp).model_dump()
        sp_dict["product_name"] = sp.product.name if sp.product else None
        sp_dict["supplier_name"] = sp.supplier.name if sp.supplier else None
        sp_dict["aliases"] = [
            alias_schema.SupplierProductAlias.model_validate(alias)
            for alias in crud_supplier_product_alias.get_active_by_supplier_and_product(
                db=db, supplier_id=sp.supplier_id, product_id=sp.product_id
            )
        ]
        result.append(supplier_product_schema.SupplierProductWithDetails(**sp_dict))
    return result
