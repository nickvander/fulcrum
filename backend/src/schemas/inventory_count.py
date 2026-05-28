"""Schemas for the physical-count session workflow.

The endpoint layer translates these → service-layer calls; the
service is the source of truth for validation (status transitions,
SKU lookup, quantity rules)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class InventoryCountSessionCreate(BaseModel):
    """Operator-supplied payload when starting a session."""
    location: Optional[str] = None
    notes: Optional[str] = None


class InventoryCountItemAdd(BaseModel):
    """Add a SKU to an in-progress session."""
    sku: str


class InventoryCountItemUpdate(BaseModel):
    """Set the operator's physical count for one row. `None`
    clears the count (operator scanned but hasn't counted yet)."""
    counted_quantity: Optional[int] = None


class InventoryCountItemRead(BaseModel):
    id: int
    session_id: int
    product_id: int
    variant_id: Optional[int] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    expected_quantity: int
    counted_quantity: Optional[int] = None
    added_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryCountSessionRead(BaseModel):
    """Session header — without the items list. Used by the list
    endpoint where rendering items per row would explode payloads."""
    id: int
    status: str
    location: str
    notes: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    started_by_user_id: Optional[int] = None
    started_by_email: Optional[str] = None
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class InventoryCountSessionDetail(InventoryCountSessionRead):
    """Session header + items. Used by the detail endpoint and the
    commit/cancel responses so the UI can patch in place."""
    items: List[InventoryCountItemRead] = []


class InventoryCountCommitResult(BaseModel):
    """What commit produced: adjustments written + items skipped
    (NULL count or zero delta) + the refreshed session."""
    adjustments_created: int
    items_skipped: int
    session: InventoryCountSessionDetail
