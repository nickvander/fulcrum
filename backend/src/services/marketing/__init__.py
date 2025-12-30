"""
Marketing Services Module

Provides connectors for various marketing platforms:
- Email: SMTP, Mailgun, SendGrid
- Ads: Google Ads, Meta Ads
- Social: Instagram, Facebook, TikTok, Twitter/X
"""

from typing import Dict, Type
import logging

from .base import (
    MarketingConnectorBase,
    PublishResult,
    AnalyticsData,
    ContentPayload,
)

logger = logging.getLogger(__name__)

# Connector Registry - maps connector_type to connector class
CONNECTOR_REGISTRY: Dict[str, Type[MarketingConnectorBase]] = {}

# Try to import optional connectors
try:
    from .smtp import SMTPConnector
    CONNECTOR_REGISTRY["smtp"] = SMTPConnector
except ImportError as e:
    logger.warning(f"SMTP connector not available: {e}. Install aiosmtplib to enable.")
    SMTPConnector = None  # type: ignore

# Social Connectors
try:
    from .social import (
        FacebookConnector,
        InstagramConnector,
        WhatsAppConnector,
        TikTokConnector,
        TwitterConnector,
    )
    CONNECTOR_REGISTRY["facebook"] = FacebookConnector
    CONNECTOR_REGISTRY["instagram"] = InstagramConnector
    CONNECTOR_REGISTRY["whatsapp"] = WhatsAppConnector
    CONNECTOR_REGISTRY["tiktok"] = TikTokConnector
    CONNECTOR_REGISTRY["twitter"] = TwitterConnector
except ImportError as e:
    logger.error(f"Failed to import social connectors: {e}")

def get_connector(connector_type: str, config: Dict) -> MarketingConnectorBase:
    """
    Factory function to get a connector instance.
    
    Args:
        connector_type: Type of connector (e.g., 'smtp', 'instagram')
        config: Configuration dictionary for the connector
        
    Returns:
        Initialized connector instance
        
    Raises:
        ValueError: If connector_type is not registered
    """
    if connector_type not in CONNECTOR_REGISTRY:
        available = ", ".join(CONNECTOR_REGISTRY.keys()) if CONNECTOR_REGISTRY else "(none installed)"
        raise ValueError(f"Unknown connector type: {connector_type}. Available: {available}")
    
    connector_class = CONNECTOR_REGISTRY[connector_type]
    return connector_class(config)


__all__ = [
    "MarketingConnectorBase",
    "PublishResult",
    "AnalyticsData",
    "ContentPayload",
    "CONNECTOR_REGISTRY",
    "get_connector",
    "FacebookConnector",
    "InstagramConnector",
    "WhatsAppConnector",
    "TikTokConnector",
    "TwitterConnector",
]

# Only export SMTPConnector if it was successfully imported
if SMTPConnector is not None:
    __all__.append("SMTPConnector")

