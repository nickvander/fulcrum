from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api import dependencies
from src.api.dependencies import get_db
from src.crud import crud_user_audit_log
from src.schemas import audit_log as audit_log_schema
from src.models.user import User

router = APIRouter()

@router.get("", response_model=List[audit_log_schema.UserAuditLog])
def read_audit_logs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(dependencies.get_current_active_superuser),
) -> Any:
    """
    Retrieve audit logs.
    Only accessible by superusers.
    """
    audit_logs = crud_user_audit_log.user_audit_log.get_multi(
        db, 
        skip=skip, 
        limit=limit, 
        user_id=user_id, 
        action=action,
        start_date=start_date,
        end_date=end_date
    )
    return audit_logs