from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.crud.base import CRUDBase
from src.models.user_audit_log import UserAuditLog
from src.schemas.audit_log import UserAuditLogCreate, UserAuditLogUpdate


class CRUDUserAuditLog(CRUDBase[UserAuditLog, UserAuditLogCreate, UserAuditLogUpdate]):
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UserAuditLog]:
        """Override get_multi to support filtering by user_id, action, and date range"""
        query = db.query(self.model)
        
        if user_id is not None:
            query = query.filter(self.model.user_id == user_id)
        
        if action:
            query = query.filter(self.model.action == action)

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
            
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        
        return query.order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserAuditLog]:
        """Get audit logs for a specific user (the user that the action was performed on)"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        return query.offset(skip).limit(limit).all()

    def get_by_actor(
        self,
        db: Session,
        *,
        actor_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserAuditLog]:
        """Get audit logs for actions performed by a specific user"""
        query = db.query(self.model).filter(self.model.action_performed_by == actor_id)
        return query.offset(skip).limit(limit).all()


user_audit_log = CRUDUserAuditLog(UserAuditLog)