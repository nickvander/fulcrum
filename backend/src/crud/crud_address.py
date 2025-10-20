from typing import Optional
from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.address import Address
from src.schemas.address import AddressCreate, AddressUpdate
from src.schemas.address import Address as AddressInDB

class CRUDAddress(CRUDBase[Address, AddressCreate, AddressUpdate]):
    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        is_primary: Optional[bool] = None,
        is_billing: Optional[bool] = None,
        is_shipping: Optional[bool] = None
    ) -> list[Address]:
        """Get addresses for a specific user with optional filters"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if is_primary is not None:
            query = query.filter(self.model.is_primary == is_primary)
        if is_billing is not None:
            query = query.filter(self.model.is_billing == is_billing)
        if is_shipping is not None:
            query = query.filter(self.model.is_shipping == is_shipping)
        
        return query.all()

    def set_primary_for_user(self, db: Session, *, user_id: int, address_id: int) -> Address:
        """Set a specific address as primary for a user and unset others"""
        # First unset all primary addresses for this user
        db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.is_primary == True
        ).update({"is_primary": False})
        
        # Then set the specified address as primary
        address = db.query(self.model).filter(
            self.model.id == address_id,
            self.model.user_id == user_id
        ).first()
        
        if address:
            address.is_primary = True
            db.add(address)
            db.commit()
            db.refresh(address)
        
        return address

address = CRUDAddress(Address)