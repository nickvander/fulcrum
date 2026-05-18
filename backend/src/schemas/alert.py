from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.models.alert import AlertType


class AlertRuleBase(BaseModel):
    alert_type: AlertType
    threshold: float
    window_days: int = Field(default=30, ge=1, le=365)
    cooldown_minutes: int = Field(default=720, ge=5, le=60 * 24 * 30)
    enabled: bool = True
    notify_email: EmailStr


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    threshold: Optional[float] = None
    window_days: Optional[int] = Field(default=None, ge=1, le=365)
    cooldown_minutes: Optional[int] = Field(default=None, ge=5, le=60 * 24 * 30)
    enabled: Optional[bool] = None
    notify_email: Optional[EmailStr] = None


class AlertRule(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    last_evaluated_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AlertEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_rule_id: int
    triggered_at: datetime
    payload: Optional[Dict[str, Any]] = None
    notification_sent: bool
    error: Optional[str] = None


class AlertEvaluationResult(BaseModel):
    """Returned by the /test endpoint and emitted internally by the
    evaluator. `triggered` is the boolean; `payload` carries the
    per-type evaluator output (see evaluator docstrings for the
    shape)."""
    rule_id: int
    triggered: bool
    payload: Dict[str, Any] = Field(default_factory=dict)
    notification_sent: bool = False
    skipped_reason: Optional[str] = None
    """Set when triggered=True but no notification was sent — typical
    value is "cooldown"."""


class AlertEvaluationBatchResult(BaseModel):
    """Returned by `evaluate_all_enabled_rules` for the Celery task."""
    rules_evaluated: int
    rules_triggered: int
    notifications_sent: int
    rule_results: List[AlertEvaluationResult]
