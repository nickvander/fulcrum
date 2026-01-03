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

    # AI Provider Settings (Encrypted keys)
    ai_enabled = Column(Integer, default=0) # 0=Disabled, 1=Enabled
    ai_provider = Column(String, default="google") # google, openai, anthropic, qwen
    ai_model = Column(String, nullable=True) # Override model name
    
    ai_google_api_key = Column(String, nullable=True)
    ai_openai_api_key = Column(String, nullable=True)
    ai_anthropic_api_key = Column(String, nullable=True)
    ai_qwen_api_key = Column(String, nullable=True)

    # Store Configuration
    store_domain = Column(String, nullable=True)  # e.g., "https://mystore.com"
    store_name = Column(String, nullable=True)

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

    @property
    def ai_config(self):
        """
        Construct AI config object for API response (hiding keys).
        """
        return {
            "enabled": bool(self.ai_enabled),
            "provider": self.ai_provider or "google",  # Fallback to google if None
            "model": self.ai_model,
            "google_configured": bool(self.ai_google_api_key),
            "openai_configured": bool(self.ai_openai_api_key),
            "anthropic_configured": bool(self.ai_anthropic_api_key),
            "qwen_configured": bool(self.ai_qwen_api_key)
        }
