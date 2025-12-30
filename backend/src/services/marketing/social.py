import logging
import random
from datetime import datetime

from .base import MarketingConnectorBase, PublishResult, AnalyticsData, ContentPayload

logger = logging.getLogger(__name__)

class SocialConnectorBase(MarketingConnectorBase):
    """Base class for social media connectors."""
    
    @property
    def channel_type(self) -> str:
        return "social"

    async def validate_credentials(self) -> bool:
        """
        Validate credentials. 
        For now, returns True if any token/key is present.
        """
        if self.config.get("access_token") or self.config.get("api_key"):
            return True
        # Allow simulation mode if 'simulation' is set
        if self.config.get("simulation_mode"):
            return True
        return False

    async def get_analytics(self, external_id: str) -> AnalyticsData:
        """Simulate analytics retrieval."""
        return AnalyticsData(
            impressions=random.randint(100, 5000),
            clicks=random.randint(10, 500),
            reach=random.randint(80, 4000),
            likes=random.randint(5, 200),
            shares=random.randint(0, 50),
            comments=random.randint(0, 20),
            last_updated=datetime.utcnow()
        )


class FacebookConnector(SocialConnectorBase):
    @property
    def connector_type(self) -> str:
        return "facebook"

    async def publish(self, content: ContentPayload) -> PublishResult:
        logger.info(f"Publishing to Facebook: {content.body}")
        
        if not content.body and not content.image_url:
             return PublishResult(
                success=False, 
                error_message="Facebook post requires text or image"
            )

        # In a real implementation, we would use facebook-sdk here
        # graph.put_object(parent_object='me', connection_name='feed', message=content.body)
        
        return PublishResult(
            success=True,
            external_id=f"fb_post_{int(datetime.utcnow().timestamp())}",
            external_url="https://facebook.com/12345/posts/67890",
            raw_response={"id": "67890_12345"}
        )


class InstagramConnector(SocialConnectorBase):
    @property
    def connector_type(self) -> str:
        return "instagram"

    async def publish(self, content: ContentPayload) -> PublishResult:
        logger.info(f"Publishing to Instagram: {content.body}, Image: {content.image_url}")
        
        if not content.image_url:
            return PublishResult(
                success=False, 
                error_message="Instagram posts require an image"
            )
            
        return PublishResult(
            success=True,
            external_id=f"ig_media_{int(datetime.utcnow().timestamp())}",
            external_url="https://instagram.com/p/ABC123xyz",
            raw_response={"id": "123456789"}
        )


class WhatsAppConnector(SocialConnectorBase):
    @property
    def connector_type(self) -> str:
        return "whatsapp"

    async def publish(self, content: ContentPayload) -> PublishResult:
        logger.info(f"Sending WhatsApp message: {content.body}")
        
        return PublishResult(
            success=True,
            external_id=f"wa_msg_{int(datetime.utcnow().timestamp())}",
            # WhatsApp doesn't have public URLs usually
            raw_response={"id": "wamid.HBgKL..."}
        )


class TikTokConnector(SocialConnectorBase):
    @property
    def connector_type(self) -> str:
        return "tiktok"

    async def publish(self, content: ContentPayload) -> PublishResult:
        logger.info(f"Publishing to TikTok: {content.body}, Video: {content.video_url}")
        
        if not content.video_url:
            return PublishResult(
                success=False, 
                error_message="TikTok posts require a video URL"
            )

        return PublishResult(
            success=True,
            external_id=f"ttk_video_{int(datetime.utcnow().timestamp())}",
            external_url="https://www.tiktok.com/@user/video/1234567890",
            raw_response={"id": "1234567890"}
        )


class TwitterConnector(SocialConnectorBase):
    @property
    def connector_type(self) -> str:
        return "twitter"

    async def publish(self, content: ContentPayload) -> PublishResult:
        logger.info(f"Tweeting: {content.body}")
        
        if len(content.body) > 280:
             return PublishResult(
                success=False, 
                error_message="Tweet exceeds 280 characters"
            )

        return PublishResult(
            success=True,
            external_id=f"tw_status_{int(datetime.utcnow().timestamp())}",
            external_url="https://twitter.com/user/status/1234567890",
            raw_response={"id": "1234567890"}
        )
