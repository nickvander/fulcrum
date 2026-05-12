from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .product import ProductImage


class StockTransferStatus(str, Enum):
    DRAFT = "draft"
    SHIPPED = "shipped"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class StockTransferProductRef(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    images: Optional[List[ProductImage]] = []

    model_config = ConfigDict(from_attributes=True)


# --- Items ---
class StockTransferItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    qty_planned: int = Field(ge=0, default=0)


class StockTransferItemCreate(StockTransferItemBase):
    pass


class StockTransferItem(StockTransferItemBase):
    id: int
    transfer_id: int
    qty_shipped: int = 0
    qty_received: int = 0
    product: Optional[StockTransferProductRef] = None

    model_config = ConfigDict(from_attributes=True)


# --- Receive request line ---
class StockTransferReceiveItem(BaseModel):
    transfer_item_id: Optional[int] = None
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(gt=0)


# --- Allocation planner ---
class StockAllocationEntry(BaseModel):
    product_id: int
    dest_location: str
    qty_planned: int = Field(gt=0)


class StockAllocationPlanRequest(BaseModel):
    notes: Optional[str] = None
    allocations: List[StockAllocationEntry]


class InventorySnapshotRow(BaseModel):
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    by_location: dict
    total: int


class ReconciliationRow(BaseModel):
    transfer_id: int
    transfer_status: str
    dest_location: str
    product_id: int
    product_name: Optional[str] = None
    qty_shipped: int
    qty_received: int
    delta: int
    shipped_at: Optional[str] = None
    received_at: Optional[str] = None


# --- Transfer ---
class StockTransferBase(BaseModel):
    source_location: str = "default"
    dest_location: str
    notes: Optional[str] = None


class StockTransferCreate(StockTransferBase):
    items: List[StockTransferItemCreate] = []


class StockTransferUpdate(BaseModel):
    dest_location: Optional[str] = None
    source_location: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[StockTransferItemCreate]] = None


class StockTransfer(StockTransferBase):
    id: int
    status: StockTransferStatus
    external_inbound_id: Optional[str] = None
    shipped_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[StockTransferItem] = []

    model_config = ConfigDict(from_attributes=True)
