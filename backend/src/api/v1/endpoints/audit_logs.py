from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src import crud, models
from src.schemas import audit_log as audit_log_schema
from src.api import dependencies

router = APIRouter()


@router.get("/", response_model=List[audit_log_schema.UserAuditLog], tags=["audit-logs"])
def read_user_audit_logs(
    db: Session = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> List[models.UserAuditLog]:
    """
    Get audit logs for user management operations.
    Only admin users can access this endpoint.
    Supports filtering by user_id and action type.
    """
    audit_logs = crud.user_audit_log.get_multi(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        action=action
    )
    return audit_logs


@router.get("/{user_id}", response_model=List[audit_log_schema.UserAuditLog], tags=["audit-logs"])
def read_user_audit_logs_by_user(
    user_id: int,
    db: Session = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> List[models.UserAuditLog]:
    """
    Get audit logs for a specific user.
    Only admin users can access this endpoint.
    """
    # Verify the user exists
    target_user = crud.user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    audit_logs = crud.user_audit_log.get_by_user(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    return audit_logs


@router.get("/actor/{actor_id}", response_model=List[audit_log_schema.UserAuditLog], tags=["audit-logs"])
def read_audit_logs_by_actor(
    actor_id: int,
    db: Session = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> List[models.UserAuditLog]:
    """
    Get audit logs for actions performed by a specific user.
    Only admin users can access this endpoint.
    """
    # Verify the actor exists
    actor = crud.user.get(db, id=actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="User not found")
    
    audit_logs = crud.user_audit_log.get_by_actor(
        db,
        actor_id=actor_id,
        skip=skip,
        limit=limit
    )
    return audit_logs