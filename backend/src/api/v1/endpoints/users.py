import os
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from src import crud, models, schemas
from src.schemas import token as token_schema, user as user_schema
from src.api import dependencies
from src.config import settings
from src.core import security
from src.core.ratelimit import limiter

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)


@router.post("/", response_model=user_schema.User, tags=["users"])
def create_user(
    *,
    db: Session = Depends(dependencies.get_db),
    user_in: user_schema.UserCreate,
    current_user: Optional[models.User] = Depends(dependencies.get_current_user_optional),
) -> user_schema.User:
    # Check privileges if trying to create an admin or superuser
    if user_in.user_type == "admin" or user_in.is_superuser:
        if not current_user or not crud.user.is_superuser(current_user):
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )

    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    user = crud.user.create(db, obj_in=user_in)
    
    # If created by admin/superuser and force_password_change was not explicitly set, default to True
    if current_user and (crud.user.is_superuser(current_user) or current_user.user_type == "admin") and user_in.force_password_change is None:
        user.force_password_change = True
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user_schema.User.from_orm(user)


@router.post("/change-password", tags=["users"])
def change_password(
    *,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
    password_data: schemas.PasswordChange,
) -> dict:
    """
    Change password for the current user.
    Required when force_password_change is True.
    """
    # Verify current password
    if not security.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    # Check if new password is the same as old password
    if security.verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current password")
        
    # Update password
    hashed_password = security.get_password_hash(password_data.new_password)
    current_user.hashed_password = hashed_password
    current_user.force_password_change = False
    
    db.add(current_user)
    db.commit()
    
    return {"message": "Password updated successfully"}


@router.post("/login/access-token", response_model=token_schema.Token, tags=["users"])
@limiter.limit("5/minute")
def login_access_token(
    request: Request,
    db: Session = Depends(dependencies.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/", response_model=List[user_schema.User], tags=["users"])
def read_users(
    db: Session = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> List[user_schema.User]:
    """
    Retrieve users.
    Only admin users can access this endpoint.
    Supports filtering by user_type, is_active, and search.
    """
    users = crud.user.get_multi(
        db, 
        skip=skip, 
        limit=limit, 
        user_type=user_type,
        is_active=is_active,
        search=search
    )
    return [user_schema.User.from_orm(user) for user in users]





@router.post("/password-reset-request", tags=["users"])
@limiter.limit("3/minute")
def request_password_reset(
    request: Request,
    *,
    db: Session = Depends(dependencies.get_db),
    email_data: user_schema.UserEmail,
) -> dict:
    """
    Request a password reset token to be sent via email.
    """
    # Find user by email
    user = crud.user.get_by_email(db, email=email_data.email)
    if not user:
        # Don't reveal that the email doesn't exist for security reasons
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Create a password reset token
    reset_token = crud.password_reset_token.create_reset_token(db, user_id=user.id)
    
    # Send password reset email
    from src.services.email_service import get_email_service
    email_service = get_email_service()
    
    # Get base URL from request or environment
    base_url = os.getenv("FRONTEND_URL", "http://localhost:4200")
    
    try:
        email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token.token,
            base_url=base_url
        )
        logger.info(f"Password reset email sent to: {user.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        # Don't reveal the error to the user for security
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset", tags=["users"])
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    *,
    db: Session = Depends(dependencies.get_db),
    reset_data: schemas.PasswordResetTokenVerify,
) -> dict:
    """
    Reset a user's password using a reset token.
    """
    # Verify the reset token
    reset_token = crud.password_reset_token.get_valid_token(db, token=reset_data.token)
    
    if not reset_token or reset_token.used:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Get the user to be updated
    user = reset_token.user
    
    # Hash the new password
    hashed_password = security.get_password_hash(reset_data.new_password)
    
    # Update the user's password
    user.hashed_password = hashed_password
    
    # Mark the reset token as used
    crud.password_reset_token.mark_token_as_used(db, token=reset_token)
    
    db.add(user)
    db.commit()
    
    logger.info(f"Password reset successful for user: {user.email}")
    
    # Record audit log for password reset
    from src.models.user_audit_log import UserAuditLog
    audit_log = UserAuditLog(
        user_id=user.id,
        action_performed_by=user.id,  # self-initiated reset
        action='password_reset',
        details="Password reset using token",
        ip_address=request.client.host if request else "",
        user_agent=request.headers.get("user-agent", "") if request else ""
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Password reset successful"}


@router.post("/{user_id}/admin-reset-password", tags=["users"])
def admin_reset_password(
    user_id: int,
    *,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin),
    request: Request,
) -> dict:
    """
    Admin reset a user's password - generates a new random password and can optionally send notification.
    This endpoint is only accessible by admin users and is audited.
    """
    # Get the user to reset password for
    target_user = crud.user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    
    # Generate a secure random password
    import secrets
    import string
    # Generate a secure random password - 16 characters with mixed case, numbers and symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = ''.join(secrets.choice(alphabet) for _ in range(16))
    
    # Hash the new password
    hashed_password = security.get_password_hash(new_password)
    
    # Update the user's password
    target_user.hashed_password = hashed_password
    db.add(target_user)
    db.commit()
    
    logger.info(f"Admin {current_user.email} reset password for user {target_user.email}")
    
    # Record audit log for admin password reset
    from src.models.user_audit_log import UserAuditLog
    audit_log = UserAuditLog(
        user_id=target_user.id,
        action_performed_by=current_user.id,  # admin initiated
        action='admin_password_reset',
        details=f"Password reset by admin {current_user.email}",
        ip_address=request.client.host if request else "",
        user_agent=request.headers.get("user-agent", "") if request else ""
    )
    db.add(audit_log)
    db.commit()
    
    # Note: In a real implementation, you would send the new password to the user via secure channel
    # For development/testing purposes, we return the password (this would be removed in production)
    return {
        "message": "Password reset successfully. New password has been generated and should be communicated to the user securely.",
        "new_password": new_password
    }


@router.get("/profile", response_model=user_schema.User, tags=["users"])
def read_user_profile(
    current_user: models.User = Depends(dependencies.get_current_user),
) -> user_schema.User:
    """
    Get current user's profile information.
    """
    return user_schema.User.from_orm(current_user)


@router.put("/profile", response_model=user_schema.User, tags=["users"])
def update_user_profile(
    *,
    db: Session = Depends(dependencies.get_db),
    user_in: user_schema.UserUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
) -> user_schema.User:
    """
    Update current user's profile information.
    """
    # Only update allowed fields for profile (not superuser status or user type)
    user_in_data = user_in.model_dump(exclude_unset=True)
    
    # Remove sensitive fields that shouldn't be changed by regular users
    allowed_fields = {"first_name", "last_name", "email", "is_active", "password", "avatar"}
    filtered_data = {k: v for k, v in user_in_data.items() if k in allowed_fields}
    
    # For non-superusers, they shouldn't be able to change their own is_active status
    if not crud.user.is_superuser(current_user) and "is_active" in filtered_data:
        del filtered_data["is_active"]
    
    # Update user
    user = crud.user.update(db, db_obj=current_user, obj_in=user_in.__class__(**filtered_data))
    return user_schema.User.from_orm(user)


@router.get("/{user_id}", response_model=user_schema.User, tags=["users"])
def read_user_by_id(
    user_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
) -> user_schema.User:
    """
    Get a specific user by id.
    Admins can access all users, regular users can only access themselves.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Allow user to access their own profile
    if user.id == current_user.id:
        return user_schema.User.from_orm(user)
    
    # Only admin users can access other users
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return user_schema.User.from_orm(user)


@router.put("/{user_id}", response_model=user_schema.User, tags=["users"])
def update_user(
    *,
    db: Session = Depends(dependencies.get_db),
    user_id: int,
    user_in: user_schema.UserUpdate,
    current_user: models.User = Depends(dependencies.get_current_admin),
) -> user_schema.User:
    """
    Update a user.
    Only admin users can update other users.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    
    # Only admin users can update other users
    updated_user = crud.user.update(db, db_obj=user, obj_in=user_in)
    return user_schema.User.from_orm(updated_user)


@router.delete("/{user_id}", tags=["users"])
def delete_user(
    user_id: int,
    *,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin),
    request: Request,
) -> dict:
    """
    Deactivate a user account (soft delete).
    Only admin users can deactivate other users.
    This marks the user as inactive rather than permanently deleting them.
    """
    # Get the user to be deactivated
    target_user = crud.user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    
    # Make sure the user is not trying to deactivate themselves
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account",
        )
    
    # Update the user's is_active status to False
    target_user.is_active = False
    db.add(target_user)
    db.commit()
    db.refresh(target_user)
    
    # Record audit log for deactivation
    from src.models.user_audit_log import UserAuditLog
    audit_log = UserAuditLog(
        user_id=target_user.id,
        action_performed_by=current_user.id,  # admin initiated
        action='deactivate_user',
        details=f"User {target_user.email} deactivated by admin {current_user.email}",
        ip_address=request.client.host if request else "",
        user_agent=request.headers.get("user-agent", "") if request else ""
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.delete("/{user_id}/permanent", tags=["users"])
def delete_user_permanent(
    user_id: int,
    *,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_admin),
    request: Request,
) -> dict:
    """
    Permanently delete a user with audit logging.
    Only admin users can permanently delete other users.
    This is a hard delete that removes the user record completely from the database.
    """
    # Get the user to be deleted for audit logging
    target_user = crud.user.get(db, id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    
    # Make sure the user is not trying to delete themselves
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot permanently delete your own account",
        )
    
    # Get IP address and user agent for audit log
    ip_address = request.client.host if request else ""
    user_agent = request.headers.get("user-agent", "") if request else ""
    
    # Perform permanent deletion with audit logging
    success = crud.user.hard_delete(
        db, 
        id=user_id, 
        actor_id=current_user.id,
        details=f"User {target_user.email} ({target_user.employee_id}) permanently deleted by {current_user.email}",
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="The user could not be permanently deleted",
        )
    
    return {"message": "User permanently deleted successfully"}
