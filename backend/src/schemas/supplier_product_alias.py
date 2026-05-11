from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SupplierProductAliasBase(BaseModel):
    supplier_id: int
    product_id: int
    variant_id: Optional[int] = None
    alias_sku: Optional[str] = None
    alias_name: Optional[str] = None
    source: str = "po_confirmation"
    confidence: float = 1.0


class SupplierProductAliasCreate(SupplierProductAliasBase):
    pass


class SupplierProductAliasUpdate(BaseModel):
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    alias_sku: Optional[str] = None
    alias_name: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    is_active: Optional[bool] = None


class SupplierProductAlias(SupplierProductAliasBase):
    id: int
    normalized_sku: Optional[str] = None
    normalized_name: Optional[str] = None
    match_count: int = 0
    is_active: bool = True
    last_matched_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    product_name: Optional[str] = None
    variant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
