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

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/", response_model=user_schema.User, tags=["users"])
def create_user(
    *,
    db: Session = Depends(dependencies.get_db),
    user_in: user_schema.UserCreate,
) -> user_schema.User:
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db, obj_in=user_in)
    return user_schema.User.from_orm(user)


@router.post("/login/access-token", response_model=token_schema.Token, tags=["users"])
def login_access_token(
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
def request_password_reset(
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
    
    # In a real implementation, we would send the reset token via email here
    # For now, we'll just log it
    logger.info(f"Password reset token created: {reset_token.token} for user: {user.email}")
    
    # TODO: Implement actual email sending with the reset token
    # send_reset_email(user.email, reset_token.token)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset", tags=["users"])
def reset_password(
    *,
    db: Session = Depends(dependencies.get_db),
    reset_data: schemas.PasswordResetTokenVerify,
    request: Request,
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
        details=f"Password reset using token",
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
    # For now, we return a success message
    return {"message": "Password reset successfully. New password has been generated and should be communicated to the user securely."}


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
    allowed_fields = {"first_name", "last_name", "email", "is_active", "password"}
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
