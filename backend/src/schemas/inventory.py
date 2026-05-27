from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from src.models.inventory import InventoryAdjustmentReasonCode


# Set of valid reason codes, exposed as a Pydantic-friendly tuple
# of strings. We accept the string form here (not the enum) so the
# frontend can post lower-case values; the validator below enforces
# the set at the API boundary.
_REASON_CODE_VALUES = tuple(code.value for code in InventoryAdjustmentReasonCode)


class StockAdjustment(BaseModel):
    adjustment: int
    reason: Optional[str] = None  # Free-text note from the caller
    # Typed taxonomy — drives the audit-page filter. Operator-facing
    # adjustments default to MANUAL when omitted; system-initiated
    # callers go straight through the service layer with the right
    # enum value and don't touch this schema.
    reason_code: Optional[str] = None

    @field_validator("reason_code")
    @classmethod
    def _validate_reason_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in _REASON_CODE_VALUES:
            raise ValueError(
                f"Unknown reason_code '{v}'. Expected one of: {', '.join(_REASON_CODE_VALUES)}"
            )
        return v


class InventoryItem(BaseModel):
    id: int
    product_id: Optional[int] = None  # Now optional to support variants-only inventory
    variant_id: Optional[int] = None  # Added for variant support
    quantity: int
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class InventoryAdjustment(BaseModel):
    id: int
    product_id: Optional[int] = None  # Now optional to support variants-only adjustments
    variant_id: Optional[int] = None  # Added for variant support
    adjustment: int  # Positive for additions, negative for subtractions
    reason: Optional[str] = None
    reason_code: Optional[str] = None  # See InventoryAdjustmentReasonCode for valid values
    timestamp: Optional[datetime] = None  # Timestamp of the adjustment
    created_at: Optional[datetime] = None  # Added for consistency
    created_by: Optional[str] = None  # Made optional to handle existing records

    model_config = ConfigDict(from_attributes=True)
