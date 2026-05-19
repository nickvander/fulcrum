"""
Alerting models. A user configures `AlertRule`s for low margin, sales
dips, or stockout risk; the periodic `evaluate_alerts` Celery task fires
each rule and writes an `AlertEvent` row + an email when the condition
matches and we're outside the cooldown window.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class AlertType(str, enum.Enum):
    """First-class alert types. Each new type needs an evaluator and a
    unit test — see `services/alert_evaluation_service.py`.

    Stored as `String` (not a PG enum) on the column to keep the
    migration / SQLAlchemy enum-create dance out of the way; the
    pydantic schema enforces the constraint at the API boundary."""
    LOW_MARGIN = "low_margin"
    SALES_DIP = "sales_dip"
    STOCKOUT_RISK = "stockout_risk"
    REFUND_RATE_SPIKE = "refund_rate_spike"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_type = Column(String(32), nullable=False, index=True)
    # Type-specific threshold. Interpretation per type:
    #   low_margin:    minimum margin % — alert when ANY product's
    #                  margin_pct < threshold over the window.
    #   sales_dip:     drop percent — alert when (prev_window_revenue -
    #                  curr_window_revenue) / prev_window_revenue * 100
    #                  >= threshold.
    #   stockout_risk: count — alert when the number of products in
    #                  the "out" + "imminent" buckets >= threshold.
    threshold = Column(Float, nullable=False)
    window_days = Column(Integer, nullable=False, default=30)
    # Suppresses notifications for `cooldown_minutes` after a successful
    # send. Prevents spamming the operator when a condition is sticky
    # (e.g. inventory is below threshold for a week — they got one
    # email, they don't need 168 hourly reminders).
    cooldown_minutes = Column(Integer, nullable=False, default=60 * 12)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    notify_email = Column(String, nullable=False)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")


class AlertEvent(Base):
    """One row per fired alert (a notification was attempted). Acts as
    an audit trail — answers "why didn't I get an email" by recording
    `notification_sent=False` + an `error` string when the SMTP send
    failed. Skipped-because-cooldown alerts do NOT get a row here; the
    rule's `last_evaluated_at` reflects that we checked."""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Per-type evaluation summary. Stable schema: each evaluator
    # documents its payload shape next to the evaluator function.
    payload = Column(JSON, nullable=True)
    notification_sent = Column(Boolean, nullable=False, default=False)
    error = Column(String(500), nullable=True)

    rule = relationship("AlertRule", back_populates="events")
