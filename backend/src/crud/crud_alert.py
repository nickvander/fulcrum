from typing import List, Optional

from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.alert import AlertRule, AlertEvent
from src.schemas.alert import AlertRuleCreate, AlertRuleUpdate


class CRUDAlertRule(CRUDBase[AlertRule, AlertRuleCreate, AlertRuleUpdate]):
    def list_for_user(self, db: Session, *, user_id: int) -> List[AlertRule]:
        return (
            db.query(AlertRule)
            .filter(AlertRule.user_id == user_id)
            .order_by(AlertRule.id.asc())
            .all()
        )

    def list_enabled(self, db: Session) -> List[AlertRule]:
        return db.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()

    def get_for_user(self, db: Session, *, user_id: int, rule_id: int) -> Optional[AlertRule]:
        return (
            db.query(AlertRule)
            .filter(AlertRule.id == rule_id, AlertRule.user_id == user_id)
            .first()
        )

    def create_for_user(
        self, db: Session, *, user_id: int, obj_in: AlertRuleCreate
    ) -> AlertRule:
        data = obj_in.model_dump()
        rule = AlertRule(user_id=user_id, **data)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule


alert_rule = CRUDAlertRule(AlertRule)


def list_events_for_rule(db: Session, *, rule_id: int, limit: int = 50) -> List[AlertEvent]:
    return (
        db.query(AlertEvent)
        .filter(AlertEvent.alert_rule_id == rule_id)
        .order_by(AlertEvent.triggered_at.desc())
        .limit(limit)
        .all()
    )
