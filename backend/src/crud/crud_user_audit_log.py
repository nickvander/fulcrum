from typing import Optional
from src.crud.base import CRUDBase
from src.models.user_audit_log import UserAuditLog
from src.schemas.user_audit_log import UserAuditLogCreate, UserAuditLogUpdate
from sqlalchemy.orm import Session


class CRUDUserAuditLog(CRUDBase[UserAuditLog, UserAuditLogCreate, UserAuditLogUpdate]):
    pass


user_audit_log = CRUDUserAuditLog(UserAuditLog)