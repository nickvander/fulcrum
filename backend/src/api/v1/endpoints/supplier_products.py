"""
API endpoints for SupplierProduct (multi-source product management).
"""
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.crud.crud_supplier_product import supplier_product as crud_supplier_product
from src.crud.crud_supplier_product_alias import supplier_product_alias as crud_supplier_product_alias
from src.crud.crud_product import product as crud_product
from src.crud.crud_supplier import supplier as crud_supplier
from src.schemas import supplier_product as sp_schema
from src.schemas import supplier_product_alias as alias_schema

router = APIRouter()


@router.get("/by-product/{product_id}", response_model=List[sp_schema.SupplierProductWithDetails])
def get_suppliers_for_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
) -> Any:
    """
    Get all suppliers for a product.
    Returns list sorted by primary first, then by cost.
    """
    product = crud_product.get(db=db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    supplier_products = crud_supplier_product.get_by_product(db=db, product_id=product_id)
    
    # Add names for display
    result = []
    for sp in supplier_products:
        sp_dict = sp_schema.SupplierProduct.model_validate(sp).model_dump()
        sp_dict["product_name"] = product.name
        sp_dict["supplier_name"] = sp.supplier.name if sp.supplier else None
        sp_dict["aliases"] = [
            alias_schema.SupplierProductAlias.model_validate(alias)
            for alias in crud_supplier_product_alias.get_active_by_supplier_and_product(
                db=db, supplier_id=sp.supplier_id, product_id=sp.product_id
            )
        ]
        result.append(sp_schema.SupplierProductWithDetails(**sp_dict))
    
    return result


@router.get("/by-supplier/{supplier_id}", response_model=List[sp_schema.SupplierProductWithDetails])
def get_products_for_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
) -> Any:
    """
    Get all products from a supplier.
    """
    supplier = crud_supplier.get(db=db, id=supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    supplier_products = crud_supplier_product.get_by_supplier(db=db, supplier_id=supplier_id)
    
    # Add names for display
    result = []
    for sp in supplier_products:
        sp_dict = sp_schema.SupplierProduct.model_validate(sp).model_dump()
        sp_dict["product_name"] = sp.product.name if sp.product else None
        sp_dict["supplier_name"] = supplier.name
        sp_dict["aliases"] = [
            alias_schema.SupplierProductAlias.model_validate(alias)
            for alias in crud_supplier_product_alias.get_active_by_supplier_and_product(
                db=db, supplier_id=sp.supplier_id, product_id=sp.product_id
            )
        ]
        result.append(sp_schema.SupplierProductWithDetails(**sp_dict))
    
    return result


@router.get("/aliases", response_model=List[alias_schema.SupplierProductAlias])
def read_supplier_product_aliases(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
) -> Any:
    """
    Read active learned aliases for a supplier.
    """
    supplier = crud_supplier.get(db=db, id=supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return [
        alias_schema.SupplierProductAlias.model_validate(alias)
        for alias in crud_supplier_product_alias.get_active_by_supplier(db=db, supplier_id=supplier_id)
    ]


@router.post("/aliases", response_model=alias_schema.SupplierProductAlias)
def create_supplier_product_alias(
    *,
    db: Session = Depends(get_db),
    alias_in: alias_schema.SupplierProductAliasCreate,
) -> Any:
    """
    Create or reactivate a learned supplier alias.
    """
    if not crud_supplier.get(db=db, id=alias_in.supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    if not crud_product.get(db=db, id=alias_in.product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    alias = crud_supplier_product_alias.upsert_learned_alias(
        db=db,
        supplier_id=alias_in.supplier_id,
        product_id=alias_in.product_id,
        variant_id=alias_in.variant_id,
        alias_sku=alias_in.alias_sku,
        alias_name=alias_in.alias_name,
        source=alias_in.source,
        confidence=alias_in.confidence,
    )
    if not alias:
        raise HTTPException(status_code=400, detail="Alias SKU or name is required")

    db.commit()
    db.refresh(alias)
    return alias_schema.SupplierProductAlias.model_validate(alias)


@router.delete("/aliases/{id}", response_model=alias_schema.SupplierProductAlias)
def delete_supplier_product_alias(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Undo a learned alias by deactivating it.
    """
    alias = crud_supplier_product_alias.deactivate(db=db, id=id)
    if not alias:
        raise HTTPException(status_code=404, detail="Supplier product alias not found")
    return alias_schema.SupplierProductAlias.model_validate(alias)


@router.post("/", response_model=sp_schema.SupplierProduct)
def create_supplier_product(
    *,
    db: Session = Depends(get_db),
    sp_in: sp_schema.SupplierProductCreate,
) -> Any:
    """
    Create a new supplier-product relationship.
    """
    # Check if relationship already exists
    existing = crud_supplier_product.get_by_product_and_supplier(
        db=db, product_id=sp_in.product_id, supplier_id=sp_in.supplier_id
    )
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="This product-supplier relationship already exists"
        )
    
    # Verify product and supplier exist
    if not crud_product.get(db=db, id=sp_in.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    if not crud_supplier.get(db=db, id=sp_in.supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    return crud_supplier_product.create(db=db, obj_in=sp_in)


@router.put("/{id}", response_model=sp_schema.SupplierProduct)
def update_supplier_product(
    *,
    db: Session = Depends(get_db),
    id: int,
    sp_in: sp_schema.SupplierProductUpdate,
) -> Any:
    """
    Update a supplier-product relationship.
    """
    sp = crud_supplier_product.get(db=db, id=id)
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier-product relationship not found")
    
    return crud_supplier_product.update(db=db, db_obj=sp, obj_in=sp_in)


@router.delete("/{id}")
def delete_supplier_product(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Delete a supplier-product relationship.
    """
    sp = crud_supplier_product.get(db=db, id=id)
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier-product relationship not found")
    
    crud_supplier_product.remove(db=db, id=id)
    return {"message": "Deleted successfully"}


@router.post("/{id}/set-primary", response_model=sp_schema.SupplierProduct)
def set_as_primary_supplier(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Set a supplier as the primary supplier for a product.
    Unsets any other primary for the same product.
    """
    sp = crud_supplier_product.get(db=db, id=id)
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier-product relationship not found")
    
    result = crud_supplier_product.set_as_primary(
        db=db, product_id=sp.product_id, supplier_product_id=id
    )
    return result
