from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src import crud, models
from src.schemas import address as address_schema
from src.api import dependencies

router = APIRouter()


@router.post("/", response_model=address_schema.Address, tags=["addresses"])
def create_address(
    *,
    db: Session = Depends(dependencies.get_db),
    address_in: address_schema.AddressCreate,
    current_user: models.User = Depends(dependencies.get_current_user),
) -> models.Address:
    """
    Create a new address for the current user.
    """
    # Create the address with the current user's ID
    db_obj = models.Address(
        street=address_in.street,
        city=address_in.city,
        state=address_in.state,
        postal_code=address_in.postal_code,
        country=address_in.country,
        is_primary=address_in.is_primary,
        is_billing=address_in.is_billing,
        is_shipping=address_in.is_shipping,
        user_id=current_user.id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=List[address_schema.Address], tags=["addresses"])
def read_addresses(
    db: Session = Depends(dependencies.get_db),
    is_primary: Optional[bool] = None,
    is_billing: Optional[bool] = None,
    is_shipping: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_user),
) -> List[models.Address]:
    """
    Get addresses for the current user.
    Supports filtering by address type (primary, billing, shipping).
    """
    addresses = crud.address.get_by_user(
        db,
        user_id=current_user.id,
        is_primary=is_primary,
        is_billing=is_billing,
        is_shipping=is_shipping
    )
    return addresses


@router.get("/{address_id}", response_model=address_schema.Address, tags=["addresses"])
def read_address(
    address_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
) -> models.Address:
    """
    Get a specific address by ID.
    User can only access their own addresses.
    """
    address = crud.address.get(db, id=address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Verify that the address belongs to the current user
    if address.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this address")
    
    return address


@router.put("/{address_id}", response_model=address_schema.Address, tags=["addresses"])
def update_address(
    *,
    db: Session = Depends(dependencies.get_db),
    address_id: int,
    address_in: address_schema.AddressUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
) -> models.Address:
    """
    Update an address.
    User can only update their own addresses.
    """
    address = crud.address.get(db, id=address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Verify that the address belongs to the current user
    if address.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this address")
    
    # Handle primary address logic
    if address_in.is_primary:
        # If making this address primary, unset other primary addresses
        crud.address.set_primary_for_user(db, user_id=current_user.id, address_id=address_id)
    else:
        # Update without special handling
        updated_address = crud.address.update(db, db_obj=address, obj_in=address_in)
        return updated_address
    
    updated_address = crud.address.update(db, db_obj=address, obj_in=address_in)
    return updated_address


@router.delete("/{address_id}", tags=["addresses"])
def delete_address(
    address_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
) -> dict:
    """
    Delete an address.
    User can only delete their own addresses.
    """
    address = crud.address.get(db, id=address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Verify that the address belongs to the current user
    if address.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this address")
    
    crud.address.remove(db, id=address_id)
    return {"message": "Address deleted successfully"}