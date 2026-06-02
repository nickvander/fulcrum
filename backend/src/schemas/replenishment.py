"""Schemas for the replenishment-to-Full planner (B4).

The planner adds the *time axis* the low-stock report lacks: it answers
"reorder from the supplier by date X" and "send N units to ML Full by
date Y" across the two-stage Mexico supply chain
(supplier -> internal warehouse -> MercadoLibre Full). Velocity is
ML-channel-scoped, mirroring the `ml_full_stockout_risk` alert
(`alert_evaluation_service._evaluate_ml_full_stockout_risk`).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class ReplenishmentRow(BaseModel):
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    supplier_id: Optional[int] = None

    # ML-channel sales velocity (units/day) over the window.
    daily_velocity: float

    # Current stock picture across the two-stage chain.
    internal_on_hand: int
    full_on_hand: int
    in_transit_to_full: int
    full_available: int  # full_on_hand + in_transit_to_full

    # Forward cover in days at current ML velocity.
    days_cover_full: float       # full_available / velocity
    days_cover_pipeline: float   # (internal + full_available) / velocity

    # Stage 2 — internal warehouse -> ML Full.
    send_to_full_qty: int             # capped at internal_on_hand
    send_to_full_by: Optional[date] = None

    # Stage 1 — supplier -> internal warehouse.
    supplier_lead_time_days: Optional[int] = None
    reorder_qty: int
    reorder_by: Optional[date] = None

    # "critical" — out of Full now (losing buy-box); "soon" — an action is
    # due today; "watch" — an action falls due within a week; "ok"
    # otherwise (such rows are filtered out of the report).
    severity: str


class ReplenishmentReport(BaseModel):
    rows: List[ReplenishmentRow]
    velocity_window_days: int
    full_transfer_lead_days: int
    target_cover_days: int
    total_send_now: int     # rows whose send_to_full_by is today or earlier
    total_reorder_now: int  # rows whose reorder_by is today or earlier
