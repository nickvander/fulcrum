from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional

class SMTPConfigBase(BaseModel):
    """SMTP email configuration for the store."""
    provider: str = "custom"  # gmail, outlook, yahoo, custom
    host: Optional[str] = None
    port: int = 587
    username: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False

class SMTPConfigCreate(SMTPConfigBase):
    """Schema for creating/updating SMTP config (includes password)."""
    password: Optional[str] = None  # Will be encrypted

class SMTPConfig(SMTPConfigBase):
    """Read schema (excludes password)."""
    is_configured: bool = False

class StoreSettingsBase(BaseModel):
    settings: Dict[str, Any] = {}
    low_inventory_days_default: int = 30
    low_stock_quantity_default: int = 10

class StoreSettingsCreate(StoreSettingsBase):
    pass

class StoreSettingsUpdate(StoreSettingsBase):
    pass

class StoreSettings(StoreSettingsBase):
    id: int
    smtp_config: Optional[SMTPConfig] = None

    model_config = ConfigDict(from_attributes=True)

