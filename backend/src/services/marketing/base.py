"""
Marketing Connectors Base Module

This module contains the abstract base class for marketing connectors and
shared data models used across all marketing integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime


class PublishResult(BaseModel):
    """Result of publishing content to a marketing platform."""
    success: bool
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Dict[str, Any] = {}


class AnalyticsData(BaseModel):
    """Analytics data retrieved from a marketing platform."""
    impressions: int = 0
    clicks: int = 0
    reach: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    conversions: int = 0
    cost: float = 0.0
    # Email-specific
    emails_sent: int = 0
    emails_opened: int = 0
    emails_bounced: int = 0
    unsubscribes: int = 0
    # Timestamps
    last_updated: Optional[datetime] = None
    raw_data: Dict[str, Any] = {}


class ContentPayload(BaseModel):
    """Standardized content payload for publishing."""
    subject: Optional[str] = None  # Email subject, ad headline
    body: str  # Main content text
    image_url: Optional[str] = None
    image_urls: List[str] = []  # Multiple images for carousel
    video_url: Optional[str] = None
    link_url: Optional[str] = None  # Call-to-action URL
    product_id: Optional[int] = None  # Linked product for context
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    extra: Dict[str, Any] = {}  # Platform-specific fields


class MarketingConnectorBase(ABC):
    """
    Abstract Base Class for all marketing platform integrations.
    
    Subclasses implement specific logic for:
    - Email: SMTP, Mailgun, SendGrid
    - Ads: Google Ads, Meta Ads
    - Social: Instagram, Facebook, TikTok, Twitter/X
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector with configuration.
        
        Args:
            config: Dictionary containing credentials and settings.
                    May include access_token, api_key, etc.
        """
        self.config = config

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return the connector type identifier (e.g., 'smtp', 'instagram')."""
        pass

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return the channel type ('email', 'paid_ad', 'social')."""
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that the stored credentials are valid.
        
        Returns:
            True if credentials are valid and connection is working.
        """
        pass

    @abstractmethod
    async def publish(self, content: ContentPayload) -> PublishResult:
        """
        Publish content to the platform.
        
        Args:
            content: Standardized content payload.
            
        Returns:
            PublishResult with success status and external references.
        """
        pass

    @abstractmethod
    async def get_analytics(self, external_id: str) -> AnalyticsData:
        """
        Retrieve analytics for published content.
        
        Args:
            external_id: The platform's ID for the published content.
            
        Returns:
            AnalyticsData with engagement metrics.
        """
        pass

    # Optional methods with default implementations

    async def get_auth_url(self, redirect_uri: str) -> Optional[str]:
        """
        Get OAuth authorization URL (for platforms requiring OAuth).
        
        Returns:
            Authorization URL or None if not applicable.
        """
        return None

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Exchange OAuth code for access tokens.
        
        Returns:
            Token data or None if not applicable.
        """
        return None

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an expired access token.
        
        Returns:
            New token data or None if not applicable.
        """
        return None

    async def delete_content(self, external_id: str) -> bool:
        """
        Delete published content from the platform.
        
        Returns:
            True if deletion was successful.
        """
        return False

    async def update_content(self, external_id: str, content: ContentPayload) -> PublishResult:
        """
        Update existing published content.
        
        Returns:
            PublishResult with updated references.
        """
        return PublishResult(
            success=False,
            error_message="Update not supported by this connector"
        )
