"""Schemas for the margin-floor repricing assistant (B6).

For each marketplace listing, compute the price that achieves a target
net-margin floor given the SKU's *real* costs — COGS plus the effective
fee + shipping rate derived from settled marketplace finance data — and
flag listings priced below that floor. v1 is margin-floor only; a
competitor / buy-box signal is deferred (see `work/future/93`).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RepricingRow(BaseModel):
    listing_id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    marketplace_id: int
    marketplace_name: str
    external_listing_id: Optional[str] = None

    cost_price: float
    current_price: float
    # Effective rates used for the floor: fee as a fraction of price,
    # shipping in absolute currency per unit.
    effective_fee_rate: float
    shipping_per_unit: float
    # 'settled' when the rates came from real marketplace finance data,
    # 'estimated' when they fell back to the marketplace default config.
    rate_source: str

    current_margin_percent: Optional[float] = None  # null when infeasible
    margin_floor_percent: float
    # Suggested price to reach the floor; null when no raise is needed or
    # the floor is mathematically infeasible (fee + floor >= 100%).
    suggested_price: Optional[float] = None
    suggested_margin_percent: Optional[float] = None

    # 'loss'       — selling below cost+fees (negative margin)
    # 'below_floor' — positive margin but under the floor
    # 'infeasible' — floor unreachable at any price for this fee rate
    status: str


class RepricingReport(BaseModel):
    rows: List[RepricingRow]
    margin_floor_percent: float
    total_loss: int        # rows currently selling at a loss
    total_below_floor: int  # rows under the floor (includes loss rows)


class ApplyPriceRequest(BaseModel):
    listing_id: int
    price: float = Field(gt=0)


class ApplyPriceResponse(BaseModel):
    listing_id: int
    marketplace_price: float

