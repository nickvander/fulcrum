"""
Pydantic schemas for Supplier Invoice.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SupplierInvoiceBase(BaseModel):
    """Base schema for supplier invoice."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None


class SupplierInvoiceCreate(SupplierInvoiceBase):
    """Schema for creating a supplier invoice."""
    po_id: int
    file_path: Optional[str] = None


class SupplierInvoiceUpdate(BaseModel):
    """Schema for updating a supplier invoice."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None


class SupplierInvoice(SupplierInvoiceBase):
    """Schema for reading a supplier invoice."""
    id: int
    po_id: int
    file_path: Optional[str] = None
    parsed_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed property for file URL
    @property
    def file_url(self) -> Optional[str]:
        if self.file_path:
            return f"/uploads/{self.file_path}"
        return None
    
    model_config = ConfigDict(from_attributes=True)
