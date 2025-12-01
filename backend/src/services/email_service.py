"""
Email service for sending transactional emails.
Provider-agnostic design - easy to swap between console logging, Resend, AWS SES, etc.
"""
import os
from typing import Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email. Returns True if successful."""
        pass


class ConsoleEmailProvider(EmailProvider):
    """Email provider that logs emails to console - perfect for development."""
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Log email to console instead of actually sending."""
        logger.info("=" * 80)
        logger.info("📧 EMAIL (Console Logger)")
        logger.info("=" * 80)
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 80)
        logger.info("HTML Content:")
        logger.info(html_content)
        if text_content:
            logger.info("-" * 80)
            logger.info("Text Content:")
            logger.info(text_content)
        logger.info("=" * 80)
        return True


class ResendEmailProvider(EmailProvider):
    """Email provider using Resend.io (3000 free emails/month)."""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        # Note: Resend SDK would be imported here when needed
        # import resend
        
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Resend API."""
        # TODO: Implement when Resend is needed
        # resend.api_key = self.api_key
        # resend.Emails.send({
        #     "from": self.from_email,
        #     "to": to_email,
        #     "subject": subject,
        #     "html": html_content,
        #     "text": text_content or ""
        # })
        logger.warning("ResendEmailProvider not yet implemented - falling back to console")
        return ConsoleEmailProvider().send_email(to_email, subject, html_content, text_content)


class EmailService:
    """Main email service - automatically selects provider based on environment."""
    
    def __init__(self):
        self.provider = self._get_provider()
        self.from_email = os.getenv("FROM_EMAIL", "noreply@fulcrum.local")
        self.from_name = os.getenv("FROM_NAME", "Fulcrum")
        
    def _get_provider(self) -> EmailProvider:
        """Select email provider based on EMAIL_PROVIDER env var."""
        provider_type = os.getenv("EMAIL_PROVIDER", "console").lower()
        
        if provider_type == "console":
            return ConsoleEmailProvider()
        elif provider_type == "resend":
            api_key = os.getenv("RESEND_API_KEY")
            if not api_key:
                logger.warning("RESEND_API_KEY not set, falling back to console")
                return ConsoleEmailProvider()
            from_email = os.getenv("FROM_EMAIL", "noreply@fulcrum.local")
            return ResendEmailProvider(api_key, from_email)
        else:
            logger.warning(f"Unknown EMAIL_PROVIDER: {provider_type}, using console")
            return ConsoleEmailProvider()
    
    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        base_url: str
    ) -> bool:
        """
        Send password reset email with token link.
        
        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            base_url: Base URL of the application (e.g., http://localhost:4200)
        
        Returns:
            True if email sent successfully
        """
        # Construct reset URL
        reset_url = f"{base_url.rstrip('/')}/auth/reset-password?token={reset_token}"
        
        # Email subject
        subject = "Reset Your Fulcrum Password"
        
        # HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1976d2; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #1976d2; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You requested to reset your password for your Fulcrum account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #eee; padding: 10px; font-size: 12px;">
                        {reset_url}
                    </p>
                    <p><strong>This link will expire in 24 hours.</strong></p>
                    <p>If you didn't request this password reset, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This is an automated email from Fulcrum. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
Reset Your Fulcrum Password

You requested to reset your password for your Fulcrum account.

Click this link to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request this password reset, you can safely ignore this email.

---
This is an automated email from Fulcrum. Please do not reply.
        """
        
        return self.provider.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
