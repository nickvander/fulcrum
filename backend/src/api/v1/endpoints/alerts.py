"""Alerting API. Per-user CRUD for `AlertRule`s plus a /test endpoint
for ad-hoc "did I set this up right?" evaluation.

Mounted at `/api/v1/alerts`. All endpoints require an authenticated
user; rules are scoped to the user — admin sees their own, not all.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_active_user, get_db
from src.core.errors import LocalizedHTTPException
from src.crud.crud_alert import alert_rule as crud_alert_rule
from src.crud.crud_alert import list_events_for_rule
from src.models.user import User
from src.schemas.alert import (
    AlertEvaluationResult,
    AlertEvent,
    AlertRule as AlertRuleSchema,
    AlertRuleCreate,
    AlertRuleUpdate,
)
from src.services.alert_evaluation_service import evaluate_rule


router = APIRouter()


@router.get("/rules", response_model=List[AlertRuleSchema])
def list_rules(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the current user's alert rules. Ordered by id asc for a
    stable list when there are 3+ rules of the same type."""
    return crud_alert_rule.list_for_user(db, user_id=current_user.id)


@router.post("/rules", response_model=AlertRuleSchema)
def create_rule(
    *,
    db: Session = Depends(get_db),
    obj_in: AlertRuleCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create a rule for the current user. No uniqueness constraint on
    (user_id, alert_type) — a user can have two `low_margin` rules at
    different thresholds (e.g. 10% to a buyer, 5% to the owner)."""
    return crud_alert_rule.create_for_user(db, user_id=current_user.id, obj_in=obj_in)


@router.get("/rules/{rule_id}", response_model=AlertRuleSchema)
def get_rule(
    rule_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rule = crud_alert_rule.get_for_user(db, user_id=current_user.id, rule_id=rule_id)
    if rule is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.alerts.ruleNotFound",
            params={"id": rule_id},
            detail="Alert rule not found",
        )
    return rule


@router.patch("/rules/{rule_id}", response_model=AlertRuleSchema)
def update_rule(
    rule_id: int,
    obj_in: AlertRuleUpdate,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rule = crud_alert_rule.get_for_user(db, user_id=current_user.id, rule_id=rule_id)
    if rule is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.alerts.ruleNotFound",
            params={"id": rule_id},
            detail="Alert rule not found",
        )
    return crud_alert_rule.update(db, db_obj=rule, obj_in=obj_in)


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rule = crud_alert_rule.get_for_user(db, user_id=current_user.id, rule_id=rule_id)
    if rule is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.alerts.ruleNotFound",
            params={"id": rule_id},
            detail="Alert rule not found",
        )
    crud_alert_rule.remove(db, id=rule_id)
    return {"deleted": rule_id}


@router.post("/rules/{rule_id}/test", response_model=AlertEvaluationResult)
def test_rule(
    rule_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Evaluate the rule against current data and — if the condition
    matches — send the email immediately, bypassing the cooldown.
    Useful for verifying the SMTP wiring + threshold settings."""
    rule = crud_alert_rule.get_for_user(db, user_id=current_user.id, rule_id=rule_id)
    if rule is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.alerts.ruleNotFound",
            params={"id": rule_id},
            detail="Alert rule not found",
        )
    result = evaluate_rule(db, rule, force_notify=True)
    db.commit()
    return result


@router.get("/rules/{rule_id}/events", response_model=List[AlertEvent])
def list_events(
    rule_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Recent fire history for one rule. Newest first, capped at 50."""
    rule = crud_alert_rule.get_for_user(db, user_id=current_user.id, rule_id=rule_id)
    if rule is None:
        raise LocalizedHTTPException(
            status_code=404,
            code="apiErrors.alerts.ruleNotFound",
            params={"id": rule_id},
            detail="Alert rule not found",
        )
    return list_events_for_rule(db, rule_id=rule_id, limit=50)
