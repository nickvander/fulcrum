from typing import Optional
from sqlalchemy.orm import Session
from src.crud.base import CRUDBase
from src.models.password_reset_token import PasswordResetToken
from src.schemas.password_reset import PasswordResetTokenCreate, PasswordResetTokenInDB
import secrets
from datetime import datetime, timedelta, timezone

class CRUDPasswordResetToken(CRUDBase[PasswordResetToken, PasswordResetTokenCreate, PasswordResetTokenInDB]):
    def create_reset_token(self, db: Session, *, user_id: int) -> PasswordResetToken:
        """Create a new password reset token for a user"""
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        # Set expiration time (e.g., 1 hour from now)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        db_obj = PasswordResetToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_valid_token(self, db: Session, *, token: str) -> Optional[PasswordResetToken]:
        """Get a valid (not expired and not used) reset token"""
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()
        
        if reset_token and not reset_token.used and reset_token.expires_at > datetime.now(timezone.utc):
            return reset_token
        return None
    
    def mark_token_as_used(self, db: Session, *, token: PasswordResetToken) -> PasswordResetToken:
        """Mark a reset token as used"""
        token.used = True
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

password_reset_token = CRUDPasswordResetToken(PasswordResetToken)