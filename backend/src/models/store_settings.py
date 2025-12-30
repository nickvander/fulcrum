from sqlalchemy import Column, Integer, JSON, String
from .base import Base

class StoreSettings(Base):
    __tablename__ = "store_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    # Using JSON for flexibility as requested for "Store Settings" generally
    settings = Column(JSON, default={})
    
    # Explicit columns for core features to ensure type safety
    low_inventory_days_default = Column(Integer, default=30)
    low_stock_quantity_default = Column(Integer, default=10)
    
    # Store-level SMTP settings (password encrypted separately)
    smtp_password_encrypted = Column(String, nullable=True)

    @property
    def smtp_config(self):
        """
        Construct SMTP config object for API response.
        Values are stored in 'settings' JSON, except password.
        """
        config = (self.settings or {}).get("smtp", {})
        return {
            "provider": config.get("provider", "custom"),
            "host": config.get("host"),
            "port": config.get("port", 587),
            "username": config.get("username"),
            "from_email": config.get("from_email"),
            "from_name": config.get("from_name"),
            "use_tls": config.get("use_tls", True),
            "use_ssl": config.get("use_ssl", False),
            "is_configured": bool(config.get("username") and self.smtp_password_encrypted)
        }

