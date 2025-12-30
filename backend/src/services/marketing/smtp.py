"""
SMTP Email Connector

Simple email sending via SMTP. This is the MVP email connector
that supports most email providers including Gmail, Outlook, etc.

Supports preset configurations for popular providers:
- Gmail: smtp.gmail.com (requires App Password)
- Outlook: smtp.office365.com
- Yahoo: smtp.mail.yahoo.com
- Custom: Any SMTP server
"""

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from datetime import datetime
import aiosmtplib

from .base import (
    MarketingConnectorBase,
    ContentPayload,
    PublishResult,
    AnalyticsData,
)


# Provider presets for easy configuration
EMAIL_PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_tls": True,
        "use_ssl": False,
        "display_name": "Gmail",
        "help_text": "Use an App Password (not your regular password). Enable 2FA in Google Account → Security → App Passwords.",
    },
    "outlook": {
        "host": "smtp.office365.com",
        "port": 587,
        "use_tls": True,
        "use_ssl": False,
        "display_name": "Outlook / Office 365",
        "help_text": "Use your Microsoft account password or an App Password if 2FA is enabled.",
    },
    "yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": 587,
        "use_tls": True,
        "use_ssl": False,
        "display_name": "Yahoo Mail",
        "help_text": "Generate an App Password in Yahoo Account → Security.",
    },
    "custom": {
        "display_name": "Custom SMTP Server",
        "help_text": "Enter your SMTP server details manually.",
    },
}


def get_smtp_config_for_provider(provider: str, username: str, password: str, from_email: str = None) -> Dict[str, Any]:
    """
    Get pre-filled SMTP configuration for a provider.
    
    Args:
        provider: Provider key ('gmail', 'outlook', 'yahoo', 'custom')
        username: SMTP username (usually email address)
        password: SMTP password or app password
        from_email: Sender email (defaults to username)
    
    Returns:
        Configuration dict ready to use with SMTPConnector
    """
    preset = EMAIL_PROVIDER_PRESETS.get(provider, {})
    return {
        "host": preset.get("host", ""),
        "port": preset.get("port", 587),
        "use_tls": preset.get("use_tls", True),
        "use_ssl": preset.get("use_ssl", False),
        "username": username,
        "password": password,
        "from_email": from_email or username,
        "provider": provider,
    }


class SMTPConnector(MarketingConnectorBase):
    """
    Email connector using SMTP protocol.
    
    Config required:
        - host: SMTP server hostname
        - port: SMTP server port (usually 587 for TLS, 465 for SSL)
        - username: SMTP username (usually email address)
        - password: SMTP password or app-specific password
        - use_tls: Whether to use STARTTLS (default: True)
        - use_ssl: Whether to use implicit SSL (default: False)
        - from_email: Sender email address
        - from_name: Sender display name (optional)
    """

    @property
    def connector_type(self) -> str:
        return "smtp"

    @property
    def channel_type(self) -> str:
        return "email"

    async def validate_credentials(self) -> bool:
        """Test SMTP connection with current credentials."""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=self.config.get("host"),
                port=self.config.get("port", 587),
                use_tls=self.config.get("use_ssl", False),
                start_tls=self.config.get("use_tls", True),
            )
            await smtp.connect()
            await smtp.login(
                self.config.get("username"),
                self.config.get("password"),
            )
            await smtp.quit()
            return True
        except Exception as e:
            print(f"SMTP validation failed: {e}")
            return False

    async def publish(self, content: ContentPayload) -> PublishResult:
        """
        Send an email.
        
        The content.extra field should contain:
            - to_emails: List of recipient email addresses
            - cc_emails: (optional) List of CC addresses
            - bcc_emails: (optional) List of BCC addresses
            - reply_to: (optional) Reply-to address
            - is_html: (optional) Whether body is HTML (default: True)
        """
        try:
            to_emails = content.extra.get("to_emails", [])
            if not to_emails:
                return PublishResult(
                    success=False,
                    error_message="No recipient emails provided in content.extra.to_emails"
                )

            # Build email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = content.subject or "(No Subject)"
            msg["From"] = f"{self.config.get('from_name', '')} <{self.config['from_email']}>".strip()
            msg["To"] = ", ".join(to_emails)
            
            if content.extra.get("cc_emails"):
                msg["Cc"] = ", ".join(content.extra["cc_emails"])
            if content.extra.get("reply_to"):
                msg["Reply-To"] = content.extra["reply_to"]

            # Add body
            is_html = content.extra.get("is_html", True)
            if is_html:
                # Add plain text version first, then HTML
                plain_text = self._html_to_plain(content.body)
                msg.attach(MIMEText(plain_text, "plain"))
                msg.attach(MIMEText(content.body, "html"))
            else:
                msg.attach(MIMEText(content.body, "plain"))

            # Collect all recipients
            all_recipients = list(to_emails)
            if content.extra.get("cc_emails"):
                all_recipients.extend(content.extra["cc_emails"])
            if content.extra.get("bcc_emails"):
                all_recipients.extend(content.extra["bcc_emails"])

            # Send email
            smtp = aiosmtplib.SMTP(
                hostname=self.config.get("host"),
                port=self.config.get("port", 587),
                use_tls=self.config.get("use_ssl", False),
                start_tls=self.config.get("use_tls", True),
            )
            await smtp.connect()
            await smtp.login(
                self.config.get("username"),
                self.config.get("password"),
            )
            await smtp.send_message(msg, recipients=all_recipients)
            await smtp.quit()

            # Generate a pseudo-ID for tracking
            email_id = f"smtp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(to_emails)}"

            return PublishResult(
                success=True,
                external_id=email_id,
                raw_response={
                    "recipients_count": len(all_recipients),
                    "subject": content.subject,
                }
            )

        except Exception as e:
            return PublishResult(
                success=False,
                error_message=str(e)
            )

    async def get_analytics(self, external_id: str) -> AnalyticsData:
        """
        SMTP doesn't provide native analytics.
        Returns empty analytics data.
        
        For tracking, consider using tracking pixels or services like
        Mailgun/SendGrid which provide delivery/open tracking.
        """
        return AnalyticsData(
            last_updated=datetime.utcnow(),
            raw_data={"note": "SMTP does not provide native analytics"}
        )

    def _html_to_plain(self, html: str) -> str:
        """Simple HTML to plain text conversion."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Convert common entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Collapse multiple whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
