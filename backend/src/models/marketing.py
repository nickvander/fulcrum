"""
Marketing Operations Models

This module contains the SQLAlchemy models for the Marketing Operations feature,
including Campaigns, Campaign Events, Marketing Connectors, and Analytics.
"""

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Date, 
    Text, Boolean, JSON, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base


class MarketingChannelType(str, enum.Enum):
    """Type of marketing channel."""
    EMAIL = "email"
    PAID_AD = "paid_ad"
    SOCIAL = "social"


class CampaignStatus(str, enum.Enum):
    """Campaign lifecycle status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConnectorType(str, enum.Enum):
    """Type of marketing connector."""
    # Email
    SMTP = "smtp"
    MAILGUN = "mailgun"
    SENDGRID = "sendgrid"
    # Ads
    GOOGLE_ADS = "google_ads"
    META_ADS = "meta_ads"
    # Social
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    TWITTER = "twitter"


# Association table for Campaign <-> Product many-to-many
campaign_products = Table(
    "campaign_products",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
)

# Association table for linking products to campaign events (e.g. for quick posts)
event_products = Table(
    "event_products",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("campaign_events.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
)


class MarketingConnector(Base):
    """
    Represents a configured marketing platform connection.
    Similar to MarketplaceCredential but for marketing channels.
    """
    __tablename__ = "marketing_connectors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    name = Column(String, nullable=False)  # User-friendly name, e.g., "My Instagram"
    connector_type = Column(String, nullable=False)  # ConnectorType enum value
    channel_type = Column(String, nullable=False)  # MarketingChannelType enum value
    
    # OAuth tokens (encrypted)
    access_token_encrypted = Column(String, nullable=True)
    refresh_token_encrypted = Column(String, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # API credentials for non-OAuth (e.g., SMTP, API keys)
    api_key_encrypted = Column(String, nullable=True)
    api_secret_encrypted = Column(String, nullable=True)
    
    # Additional config (e.g., SMTP host/port, account IDs)
    config_json = Column(JSON, default={})
    
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    events = relationship("CampaignEvent", back_populates="connector")


class Campaign(Base):
    """
    A marketing campaign that groups related marketing events.
    Campaigns can be linked to multiple products.
    """
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Campaign lifecycle
    status = Column(String, default=CampaignStatus.DRAFT.value)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Budget tracking (optional)
    budget = Column(Float, nullable=True)
    spent = Column(Float, default=0.0)
    
    # Smart Boost metadata
    is_smart_boost = Column(Boolean, default=False)  # AI-recommended campaign
    boost_reason = Column(String, nullable=True)  # e.g., "High stock, low velocity"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    products = relationship("Product", secondary=campaign_products, backref="campaigns")
    events = relationship("CampaignEvent", back_populates="campaign", cascade="all, delete-orphan")
    analytics = relationship("CampaignAnalytics", back_populates="campaign", uselist=False)


class CampaignEvent(Base):
    """
    A specific scheduled action within a campaign (email blast, ad launch, social post).
    """
    __tablename__ = "campaign_events"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    connector_id = Column(Integer, ForeignKey("marketing_connectors.id"), nullable=True)
    
    # Event details
    name = Column(String, nullable=False)
    channel_type = Column(String, nullable=False)  # MarketingChannelType enum value
    
    # Content
    content_subject = Column(String, nullable=True)  # Email subject, ad headline
    content_body = Column(Text, nullable=True)  # Email body, post text, ad copy
    content_image_url = Column(String, nullable=True)  # Primary image
    content_json = Column(JSON, default={})  # Platform-specific fields
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String, default="draft")  # draft, scheduled, publishing, published, failed
    error_message = Column(String, nullable=True)
    
    # External reference (after publishing)
    external_id = Column(String, nullable=True)  # Post ID, Ad ID, etc.
    external_url = Column(String, nullable=True)  # Link to the published content
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="events")
    connector = relationship("MarketingConnector", back_populates="events")
    analytics = relationship("EventAnalytics", back_populates="event", uselist=False)
    products = relationship("Product", secondary=event_products, backref="events")


class CampaignAnalytics(Base):
    """
    Aggregated analytics for a campaign.
    """
    __tablename__ = "campaign_analytics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), unique=True)
    
    # Reach metrics
    total_impressions = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_reach = Column(Integer, default=0)
    
    # Engagement
    total_likes = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    
    # Conversions
    total_conversions = Column(Integer, default=0)
    conversion_value = Column(Float, default=0.0)
    
    # Cost
    total_cost = Column(Float, default=0.0)
    cpc = Column(Float, nullable=True)  # Cost per click
    cpm = Column(Float, nullable=True)  # Cost per 1000 impressions
    
    # ROI
    revenue_attributed = Column(Float, default=0.0)
    roi_percentage = Column(Float, nullable=True)
    
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="analytics")


class EventAnalytics(Base):
    """
    Analytics for a specific campaign event.
    """
    __tablename__ = "event_analytics"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("campaign_events.id"), unique=True)
    
    # Reach
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    
    # Engagement
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    # Email-specific
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)
    unsubscribes = Column(Integer, default=0)
    
    # Conversions
    conversions = Column(Integer, default=0)
    conversion_value = Column(Float, default=0.0)
    
    # Cost (for ads)
    cost = Column(Float, default=0.0)
    
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    event = relationship("CampaignEvent", back_populates="analytics")


class Audience(Base):
    """
    Email lists or customer segments for targeting.
    """
    __tablename__ = "audiences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Type: email_list, segment, etc.
    audience_type = Column(String, default="email_list")
    
    # For segments, store filter criteria
    segment_criteria_json = Column(JSON, nullable=True)
    
    # Stats
    member_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    members = relationship("AudienceMember", back_populates="audience", cascade="all, delete-orphan")


class AudienceMember(Base):
    """
    Individual members of an audience (e.g., email subscribers).
    """
    __tablename__ = "audience_members"

    id = Column(Integer, primary_key=True, index=True)
    audience_id = Column(Integer, ForeignKey("audiences.id"), nullable=False)
    
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    
    # Subscription status
    is_subscribed = Column(Boolean, default=True)
    subscribed_at = Column(DateTime(timezone=True), server_default=func.now())
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    audience = relationship("Audience", back_populates="members")
