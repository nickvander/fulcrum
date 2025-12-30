"""
Marketing Operations Schemas

Pydantic schemas for Campaign, CampaignEvent, MarketingConnector, and related models.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


# ============================================================================
# Marketing Connector Schemas
# ============================================================================

class MarketingConnectorBase(BaseModel):
    name: str
    connector_type: str  # 'smtp', 'mailgun', 'instagram', etc.
    channel_type: str  # 'email', 'paid_ad', 'social'
    config_json: Optional[Dict[str, Any]] = {}
    is_active: bool = True


class MarketingConnectorCreate(MarketingConnectorBase):
    # For OAuth connectors, tokens will be set after OAuth flow
    api_key: Optional[str] = None  # Will be encrypted before storage
    api_secret: Optional[str] = None  # Will be encrypted before storage


class MarketingConnectorUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class MarketingConnector(MarketingConnectorBase):
    id: int
    user_id: Optional[int] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Note: tokens and secrets are NOT exposed in responses

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Shared Schemas
# ============================================================================

class CampaignProductSummary(BaseModel):
    """Minimal product info for campaign/event display."""
    id: int
    name: str
    sku: Optional[str] = None
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Campaign Event Schemas
# ============================================================================

class CampaignEventBase(BaseModel):
    name: str
    channel_type: str  # 'email', 'paid_ad', 'social'
    connector_id: Optional[int] = None
    content_subject: Optional[str] = None
    content_body: Optional[str] = None
    content_image_url: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = {}
    scheduled_at: Optional[datetime] = None


class CampaignEventCreate(CampaignEventBase):
    product_ids: Optional[List[int]] = []


class CampaignEventUpdate(BaseModel):
    name: Optional[str] = None
    channel_type: Optional[str] = None
    connector_id: Optional[int] = None
    content_subject: Optional[str] = None
    content_body: Optional[str] = None
    content_image_url: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    product_ids: Optional[List[int]] = None


class CampaignEvent(CampaignEventBase):
    id: int
    campaign_id: Optional[int] = None
    status: str
    published_at: Optional[datetime] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    products: List[CampaignProductSummary] = []

    model_config = ConfigDict(from_attributes=True)


class EventAnalyticsData(BaseModel):
    """Analytics for a single event."""
    impressions: int = 0
    clicks: int = 0
    reach: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_bounced: int = 0
    unsubscribes: int = 0
    conversions: int = 0
    conversion_value: float = 0.0
    cost: float = 0.0
    last_synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Campaign Schemas
# ============================================================================

class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None


class CampaignCreate(CampaignBase):
    product_ids: Optional[List[int]] = []
    events: Optional[List[CampaignEventCreate]] = []


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    product_ids: Optional[List[int]] = None


class CampaignAnalyticsData(BaseModel):
    """Aggregated analytics for a campaign."""
    total_impressions: int = 0
    total_clicks: int = 0
    total_reach: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_conversions: int = 0
    conversion_value: float = 0.0
    total_cost: float = 0.0
    cpc: Optional[float] = None
    cpm: Optional[float] = None
    revenue_attributed: float = 0.0
    roi_percentage: Optional[float] = None
    last_synced_at: Optional[datetime] = None

class Campaign(CampaignBase):
    id: int
    user_id: int
    status: str
    spent: float = 0.0
    is_smart_boost: bool = False
    boost_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Nested relations
    events: List[CampaignEvent] = []
    products: List[CampaignProductSummary] = []
    analytics: Optional[CampaignAnalyticsData] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignSummary(BaseModel):
    """Minimal campaign info for lists."""
    id: int
    name: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    events_count: int = 0
    products_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Audience Schemas
# ============================================================================

class AudienceMemberBase(BaseModel):
    email: str
    name: Optional[str] = None
    is_subscribed: bool = True
    metadata_json: Optional[Dict[str, Any]] = {}


class AudienceMemberCreate(AudienceMemberBase):
    pass


class AudienceMember(AudienceMemberBase):
    id: int
    audience_id: int
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudienceBase(BaseModel):
    name: str
    description: Optional[str] = None
    audience_type: str = "email_list"
    segment_criteria_json: Optional[Dict[str, Any]] = None


class AudienceCreate(AudienceBase):
    members: Optional[List[AudienceMemberCreate]] = []


class AudienceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    segment_criteria_json: Optional[Dict[str, Any]] = None


class Audience(AudienceBase):
    id: int
    user_id: int
    member_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AudienceWithMembers(Audience):
    members: List[AudienceMember] = []


# ============================================================================
# Smart Boost Recommendation
# ============================================================================

class SmartBoostRecommendation(BaseModel):
    """AI-generated campaign recommendation."""
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    reason: str  # e.g., "High stock, low velocity - consider clearance"
    recommended_channels: List[str] = []  # ['email', 'social']
    suggested_discount_percent: Optional[float] = None
    confidence_score: float  # 0.0 - 1.0

    model_config = ConfigDict(from_attributes=True)
