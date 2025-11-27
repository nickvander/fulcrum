from typing import Optional
from src.crud.base import CRUDBase
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import get_password_hash, verify_password
from sqlalchemy.orm import Session
import logging
import random
import string

logger = logging.getLogger(__name__)

def generate_employee_id(user_type: str) -> str:
    """
    Generate a unique employee ID based on user type
    Format: [type_prefix][random_numbers], e.g., EMP123456
    """
    if user_type == "admin":
        prefix = "ADM"
    elif user_type == "employee":
        prefix = "EMP"
    elif user_type == "customer":
        prefix = "CST"
    else:
        prefix = "USR"
    
    # Generate 6 random digits
    digits = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{digits}"

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        logger.info(f"Creating user with email: {obj_in.email}")
        try:
            hashed_password = get_password_hash(obj_in.password)
            logger.info("Password hashed successfully.")
            
            # Generate employee ID if not provided
            employee_id = obj_in.employee_id
            if not employee_id:
                # Use provided user_type or default to 'employee'
                user_type = obj_in.user_type.value if obj_in.user_type else "employee"
                employee_id = generate_employee_id(user_type)
                
                # Ensure uniqueness by checking if ID already exists
                while self.get_by_employee_id(db, employee_id=employee_id):
                    employee_id = generate_employee_id(user_type)
            
            db_obj = User(
                email=obj_in.email,
                hashed_password=hashed_password,
                employee_id=employee_id,
                first_name=obj_in.first_name,
                last_name=obj_in.last_name,
                user_type=obj_in.user_type.value if obj_in.user_type else "employee",
                is_active=obj_in.is_active,
                is_superuser=obj_in.is_superuser,
                role=obj_in.user_type.value if obj_in.user_type else "employee" if obj_in.user_type else "employee",  # Maintain compatibility with existing role field
                avatar=obj_in.avatar,
            )
            db.add(db_obj)
            logger.info("User object added to session.")
            db.flush()
            logger.info("Session flushed.")
            db.refresh(db_obj)
            logger.info("DB object refreshed.")
            return db_obj
        except Exception as e:
            logger.error(f"Error in CRUDUser.create: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_employee_id(self, db: Session, *, employee_id: str) -> Optional[User]:
        return db.query(User).filter(User.employee_id == employee_id).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        """Override update method to handle password hashing and new fields"""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle password update separately
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data["password"])
            # Remove the plain text password from update data
            del update_data["password"]
        
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> list[User]:
        """Override get_multi to support filtering and searching"""
        query = db.query(self.model)
        
        if user_type:
            query = query.filter(self.model.user_type == user_type)
        
        if is_active is not None:
            query = query.filter(self.model.is_active == is_active)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (self.model.first_name.ilike(search_filter)) |
                (self.model.last_name.ilike(search_filter)) |
                (self.model.email.ilike(search_filter)) |
                (self.model.employee_id.ilike(search_filter))
            )
        
        return query.offset(skip).limit(limit).all()

    def hard_delete(self, db: Session, *, id: int, actor_id: int, details: str = "", ip_address: str = "", user_agent: str = "") -> bool:
        """
        Permanently delete a user with audit logging.
        """

        
        # Get user for audit logging before deletion
        user = self.get(db, id=id)
        if not user:
            return False
            
        # Since cascade deletion is causing issues with missing password_reset_tokens table,
        # we'll handle the deletion more carefully by dealing with related records first
        try:
            from sqlalchemy import text
            
            # We'll create the audit log after deleting the user, to avoid foreign key issues
            # First delete related addresses
            stmt = text("DELETE FROM addresses WHERE user_id = :user_id")
            db.execute(stmt, {"user_id": id})
            
            # Delete audit logs where this user was the subject (user_id = id)
            # This is needed to satisfy the foreign key constraint when deleting the user
            stmt = text("DELETE FROM user_audit_logs WHERE user_id = :user_id")
            db.execute(stmt, {"user_id": id})
            
            # Now delete the user
            stmt = text("DELETE FROM users WHERE id = :id")
            result = db.execute(stmt, {"id": id})
            
            # After deleting the user, create the audit log for this deletion action
            # This will be a record that a user was deleted, without referencing the now-deleted user
            audit_log_details = details or f"User {user.email if user.email else f'ID {id}'} ({user.employee_id if user.employee_id else 'no-emp-id'}) permanently deleted by user ID {actor_id}"
            stmt = text("INSERT INTO user_audit_logs (action_performed_by, action, details, ip_address, user_agent) VALUES (:action_performed_by, :action, :details, :ip_address, :user_agent)")
            db.execute(stmt, {
                "action_performed_by": actor_id,
                "action": "permanent_delete", 
                "details": audit_log_details,
                "ip_address": ip_address,
                "user_agent": user_agent
            })
            
            db.commit()
            
            success = result.rowcount > 0
        except Exception as e:
            db.rollback()
            logger.error(f"Error during hard delete of user {id}: {e}")
            success = False
        
        if success:
            logger.info(f"User {id} permanently deleted by user {actor_id}")
        else:
            logger.warning(f"Attempt to permanently delete non-existent user {id} by user {actor_id}")
        
        return success


user = CRUDUser(User)
