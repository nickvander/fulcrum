"""
CRUD operations for SupplierProduct.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.supplier_product import SupplierProduct
from src.schemas.supplier_product import SupplierProductCreate, SupplierProductUpdate


class CRUDSupplierProduct(CRUDBase[SupplierProduct, SupplierProductCreate, SupplierProductUpdate]):
    """CRUD for supplier-product relationships."""
    
    def get_by_product(self, db: Session, *, product_id: int) -> List[SupplierProduct]:
        """Get all suppliers for a product."""
        return db.query(self.model).filter(
            self.model.product_id == product_id
        ).order_by(self.model.is_primary.desc(), self.model.cost_price.asc()).all()
    
    def get_by_supplier(self, db: Session, *, supplier_id: int) -> List[SupplierProduct]:
        """Get all products from a supplier."""
        return db.query(self.model).filter(
            self.model.supplier_id == supplier_id
        ).order_by(self.model.is_primary.desc()).all()
    
    def get_by_product_and_supplier(
        self, db: Session, *, product_id: int, supplier_id: int
    ) -> Optional[SupplierProduct]:
        """Get specific product-supplier relationship."""
        return db.query(self.model).filter(
            self.model.product_id == product_id,
            self.model.supplier_id == supplier_id
        ).first()
    
    def get_primary_supplier(
        self, db: Session, *, product_id: int
    ) -> Optional[SupplierProduct]:
        """Get the primary supplier for a product."""
        return db.query(self.model).filter(
            self.model.product_id == product_id,
            self.model.is_primary.is_(True)
        ).first()
    
    def set_as_primary(
        self, db: Session, *, product_id: int, supplier_product_id: int
    ) -> Optional[SupplierProduct]:
        """Set a supplier as primary for a product, unsetting others."""
        # Unset all as non-primary first
        db.query(self.model).filter(
            self.model.product_id == product_id
        ).update({"is_primary": False})
        
        # Set the specified one as primary
        sp = db.query(self.model).filter(
            self.model.id == supplier_product_id,
            self.model.product_id == product_id
        ).first()
        
        if sp:
            sp.is_primary = True
            db.commit()
            db.refresh(sp)
        
        return sp


supplier_product = CRUDSupplierProduct(SupplierProduct)
