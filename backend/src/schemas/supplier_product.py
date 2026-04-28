"""
Pydantic schemas for SupplierProduct.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SupplierProductBase(BaseModel):
    """Base schema for supplier-product relationship."""
    supplier_sku: Optional[str] = None
    supplier_product_name: Optional[str] = None
    cost_price: float = 0.0
    is_primary: bool = False
    lead_time_days: Optional[int] = None
    minimum_order_qty: float = 1.0
    notes: Optional[str] = None


class SupplierProductCreate(SupplierProductBase):
    """Schema for creating a supplier-product relationship."""
    product_id: int
    supplier_id: int


class SupplierProductUpdate(BaseModel):
    """Schema for updating a supplier-product relationship."""
    supplier_sku: Optional[str] = None
    supplier_product_name: Optional[str] = None
    cost_price: Optional[float] = None
    is_primary: Optional[bool] = None
    lead_time_days: Optional[int] = None
    minimum_order_qty: Optional[float] = None
    notes: Optional[str] = None


class SupplierProduct(SupplierProductBase):
    """Schema for reading a supplier-product relationship."""
    id: int
    product_id: int
    supplier_id: int
    last_ordered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SupplierProductWithDetails(SupplierProduct):
    """Extended schema with product and supplier names for display."""
    product_name: Optional[str] = None
    supplier_name: Optional[str] = None
