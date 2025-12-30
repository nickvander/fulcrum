"""
CRUD operations for Marketing Operations (Campaigns, Connectors, Audiences).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from src.crud.base import CRUDBase
from src.models.marketing import (
    Campaign,
    CampaignEvent,
    MarketingConnector,
    Audience,
    AudienceMember,
    CampaignAnalytics,
    EventAnalytics,
)
from src.models.product import Product
from src.schemas.marketing import (
    CampaignCreate,
    CampaignUpdate,
    CampaignEventCreate,
    CampaignEventUpdate,
    MarketingConnectorCreate,
    MarketingConnectorUpdate,
    AudienceCreate,
    AudienceUpdate,
    AudienceMemberCreate,
)
from src.core.encryption import encryption_service


class CRUDCampaign(CRUDBase[Campaign, CampaignCreate, CampaignUpdate]):
    """CRUD operations for Campaigns."""

    def get_with_relations(self, db: Session, id: int) -> Optional[Campaign]:
        """Get a campaign with all its related data."""
        return (
            db.query(Campaign)
            .options(
                joinedload(Campaign.events).joinedload(CampaignEvent.analytics),
                joinedload(Campaign.products),
                joinedload(Campaign.analytics),
            )
            .filter(Campaign.id == id)
            .first()
        )

    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Campaign]:
        """Get all campaigns for a user."""
        query = db.query(Campaign).filter(Campaign.user_id == user_id)
        if status:
            query = query.filter(Campaign.status == status)
        return query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()

    def create_with_relations(
        self, db: Session, *, obj_in: CampaignCreate, user_id: int
    ) -> Campaign:
        """Create a campaign with products and events."""
        # Create the campaign
        campaign_data = obj_in.model_dump(exclude={"product_ids", "events"})
        db_campaign = Campaign(**campaign_data, user_id=user_id)
        db.add(db_campaign)
        db.flush()

        # Link products
        if obj_in.product_ids:
            products = db.query(Product).filter(Product.id.in_(obj_in.product_ids)).all()
            db_campaign.products = products

        # Create events
        if obj_in.events:
            for event_data in obj_in.events:
                db_event = CampaignEvent(
                    campaign_id=db_campaign.id,
                    **event_data.model_dump(),
                )
                db.add(db_event)

        # Create empty analytics
        db_analytics = CampaignAnalytics(campaign_id=db_campaign.id)
        db.add(db_analytics)

        db.commit()
        db.refresh(db_campaign)
        return db_campaign

    def update_with_relations(
        self, db: Session, *, db_obj: Campaign, obj_in: CampaignUpdate
    ) -> Campaign:
        """Update a campaign and its product links."""
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"product_ids"})
        
        # Update basic fields
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Update product links if provided
        if obj_in.product_ids is not None:
            products = db.query(Product).filter(Product.id.in_(obj_in.product_ids)).all()
            db_obj.products = products

        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDCampaignEvent(CRUDBase[CampaignEvent, CampaignEventCreate, CampaignEventUpdate]):
    """CRUD operations for Campaign Events."""

    def get_by_campaign(
        self, db: Session, *, campaign_id: int
    ) -> List[CampaignEvent]:
        """Get all events for a campaign."""
        return (
            db.query(CampaignEvent)
            .filter(CampaignEvent.campaign_id == campaign_id)
            .order_by(CampaignEvent.scheduled_at)
            .all()
        )

    def get_quick_posts(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[CampaignEvent]:
        """Get all quick posts (events without a campaign)."""
        return (
            db.query(CampaignEvent)
            .filter(CampaignEvent.campaign_id.is_(None))
            .order_by(CampaignEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_for_campaign(
        self, db: Session, *, campaign_id: int, obj_in: CampaignEventCreate
    ) -> CampaignEvent:
        """Create an event for a campaign."""
        data = obj_in.model_dump(exclude={"product_ids"})
        db_event = CampaignEvent(
            campaign_id=campaign_id,
            **data,
        )
        db.add(db_event)
        
        # Link products
        if obj_in.product_ids:
            products = db.query(Product).filter(Product.id.in_(obj_in.product_ids)).all()
            db_event.products = products
        
        # Create empty analytics
        db.flush()
        db_analytics = EventAnalytics(event_id=db_event.id)
        db.add(db_analytics)
        
        db.commit()
        db.refresh(db_event)
        return db_event

    def create_quick_post(
        self, db: Session, *, obj_in: CampaignEventCreate
    ) -> CampaignEvent:
        """Create a quick post (event without a campaign)."""
        data = obj_in.model_dump(exclude={"product_ids"})
        db_event = CampaignEvent(
            campaign_id=None,
            **data,
        )
        db.add(db_event)
        
        # Link products
        if obj_in.product_ids:
            products = db.query(Product).filter(Product.id.in_(obj_in.product_ids)).all()
            db_event.products = products
        
        # Create empty analytics
        db.flush()
        db_analytics = EventAnalytics(event_id=db_event.id)
        db.add(db_analytics)
        
        db.commit()
        db.refresh(db_event)
        return db_event

    def update_status(
        self,
        db: Session,
        *,
        event_id: int,
        status: str,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[CampaignEvent]:
        """Update the status of an event after publishing."""
        event = db.query(CampaignEvent).filter(CampaignEvent.id == event_id).first()
        if event:
            event.status = status
            if external_id:
                event.external_id = external_id
            if external_url:
                event.external_url = external_url
            if error_message:
                event.error_message = error_message
            if status == "published":
                from datetime import datetime
                event.published_at = datetime.utcnow()
            db.commit()
            db.refresh(event)
        return event

    def get_events_by_date_range(
        self, db: Session, *, start_date: datetime, end_date: datetime
    ) -> List[CampaignEvent]:
        """Get all events scheduled within a date range."""
        return (
            db.query(CampaignEvent)
            .filter(
                and_(
                    CampaignEvent.scheduled_at >= start_date,
                    CampaignEvent.scheduled_at <= end_date,
                )
            )
            .order_by(CampaignEvent.scheduled_at)
            .all()
        )


class CRUDMarketingConnector(CRUDBase[MarketingConnector, MarketingConnectorCreate, MarketingConnectorUpdate]):
    """CRUD operations for Marketing Connectors."""

    def get_by_user(
        self, db: Session, *, user_id: int, active_only: bool = True
    ) -> List[MarketingConnector]:
        """Get all connectors for a user (including store-level/shared)."""
        from sqlalchemy import or_
        query = db.query(MarketingConnector).filter(
            or_(MarketingConnector.user_id == user_id, MarketingConnector.user_id.is_(None))
        )
        if active_only:
            query = query.filter(MarketingConnector.is_active.is_(True))
        return query.all()

    def get_by_type(
        self, db: Session, *, user_id: int, connector_type: str
    ) -> Optional[MarketingConnector]:
        """Get a connector by type for a user (or shared)."""
        from sqlalchemy import or_
        return (
            db.query(MarketingConnector)
            .filter(
                and_(
                    or_(MarketingConnector.user_id == user_id, MarketingConnector.user_id.is_(None)),
                    MarketingConnector.connector_type == connector_type,
                )
            )
            .first()
        )

    def create_with_encryption(
        self, db: Session, *, obj_in: MarketingConnectorCreate, user_id: Optional[int] = None
    ) -> MarketingConnector:
        """Create a connector with encrypted credentials."""
        data = obj_in.model_dump(exclude={"api_key", "api_secret"})
        db_connector = MarketingConnector(**data, user_id=user_id)
        
        # Encrypt sensitive fields
        if obj_in.api_key:
            db_connector.api_key_encrypted = encryption_service.encrypt(obj_in.api_key)
        if obj_in.api_secret:
            db_connector.api_secret_encrypted = encryption_service.encrypt(obj_in.api_secret)

        db.add(db_connector)
        db.commit()
        db.refresh(db_connector)
        return db_connector

    def get_decrypted_credentials(self, db_connector: MarketingConnector) -> Dict[str, Any]:
        """Get decrypted credentials for API use."""
        config = db_connector.config_json.copy() if db_connector.config_json else {}
        
        if db_connector.api_key_encrypted:
            config["api_key"] = encryption_service.decrypt(db_connector.api_key_encrypted)
        if db_connector.api_secret_encrypted:
            config["api_secret"] = encryption_service.decrypt(db_connector.api_secret_encrypted)
        if db_connector.access_token_encrypted:
            config["access_token"] = encryption_service.decrypt(db_connector.access_token_encrypted)
        if db_connector.refresh_token_encrypted:
            config["refresh_token"] = encryption_service.decrypt(db_connector.refresh_token_encrypted)
            
        return config


class CRUDAudience(CRUDBase[Audience, AudienceCreate, AudienceUpdate]):
    """CRUD operations for Audiences."""

    def get_by_user(
        self, db: Session, *, user_id: int
    ) -> List[Audience]:
        """Get all audiences for a user."""
        return db.query(Audience).filter(Audience.user_id == user_id).all()

    def create_with_members(
        self, db: Session, *, obj_in: AudienceCreate, user_id: int
    ) -> Audience:
        """Create an audience with initial members."""
        data = obj_in.model_dump(exclude={"members"})
        db_audience = Audience(**data, user_id=user_id)
        db.add(db_audience)
        db.flush()

        # Add members
        if obj_in.members:
            for member_data in obj_in.members:
                db_member = AudienceMember(
                    audience_id=db_audience.id,
                    **member_data.model_dump(),
                )
                db.add(db_member)
            db_audience.member_count = len(obj_in.members)

        db.commit()
        db.refresh(db_audience)
        return db_audience

    def add_member(
        self, db: Session, *, audience_id: int, member_in: AudienceMemberCreate
    ) -> AudienceMember:
        """Add a member to an audience."""
        db_member = AudienceMember(
            audience_id=audience_id,
            **member_in.model_dump(),
        )
        db.add(db_member)
        
        # Update member count
        audience = db.query(Audience).filter(Audience.id == audience_id).first()
        if audience:
            audience.member_count = (audience.member_count or 0) + 1

        db.commit()
        db.refresh(db_member)
        return db_member

    def remove_member(self, db: Session, *, member_id: int) -> bool:
        """Remove a member from an audience."""
        member = db.query(AudienceMember).filter(AudienceMember.id == member_id).first()
        if member:
            audience_id = member.audience_id
            db.delete(member)
            
            # Update member count
            audience = db.query(Audience).filter(Audience.id == audience_id).first()
            if audience:
                audience.member_count = max(0, (audience.member_count or 0) - 1)
            
            db.commit()
            return True
        return False


# Singleton instances
crud_campaign = CRUDCampaign(Campaign)
crud_campaign_event = CRUDCampaignEvent(CampaignEvent)
crud_marketing_connector = CRUDMarketingConnector(MarketingConnector)
crud_audience = CRUDAudience(Audience)
