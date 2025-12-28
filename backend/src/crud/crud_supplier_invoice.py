"""
CRUD operations for Supplier Invoice.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.supplier_invoice import SupplierInvoice
from src.schemas.supplier_invoice import SupplierInvoiceCreate, SupplierInvoiceUpdate


class CRUDSupplierInvoice(CRUDBase[SupplierInvoice, SupplierInvoiceCreate, SupplierInvoiceUpdate]):
    """CRUD for supplier invoices."""
    
    def get_by_po(self, db: Session, *, po_id: int) -> List[SupplierInvoice]:
        """Get all invoices for a purchase order."""
        return db.query(self.model).filter(
            self.model.po_id == po_id
        ).order_by(self.model.created_at.desc()).all()
    
    def get_by_invoice_number(
        self, db: Session, *, invoice_number: str
    ) -> Optional[SupplierInvoice]:
        """Get invoice by invoice number."""
        return db.query(self.model).filter(
            self.model.invoice_number == invoice_number
        ).first()


supplier_invoice = CRUDSupplierInvoice(SupplierInvoice)
