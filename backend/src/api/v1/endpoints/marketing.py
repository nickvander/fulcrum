"""
Marketing API Endpoints

Provides endpoints for managing marketing campaigns, connectors, audiences,
and related operations.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src import models
from src.api import dependencies
from src.crud.crud_marketing import (
    crud_campaign,
    crud_campaign_event,
    crud_marketing_connector,
    crud_audience,
)
from src.schemas.marketing import (
    Campaign,
    CampaignCreate,
    CampaignUpdate,
    CampaignSummary,
    CampaignEvent,
    CampaignEventCreate,
    CampaignEventUpdate,
    MarketingConnector,
    MarketingConnectorCreate,
    MarketingConnectorUpdate,
    Audience,
    AudienceCreate,
    AudienceMember,
    AudienceMemberCreate,
    SmartBoostRecommendation,
)
from src.services.marketing import get_connector, ContentPayload

router = APIRouter()


# ============================================================================
# Campaign Endpoints
# ============================================================================

@router.get("/campaigns", response_model=List[CampaignSummary])
def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """List all campaigns for the current user."""
    campaigns = crud_campaign.get_multi_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit, status=status
    )
    # Convert to summary
    return [
        CampaignSummary(
            id=c.id,
            name=c.name,
            status=c.status,
            start_date=c.start_date,
            end_date=c.end_date,
            events_count=len(c.events) if c.events else 0,
            products_count=len(c.products) if c.products else 0,
        )
        for c in campaigns
    ]


@router.post("/campaigns", response_model=Campaign, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_in: CampaignCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Create a new marketing campaign."""
    return crud_campaign.create_with_relations(db, obj_in=campaign_in, user_id=current_user.id)


@router.get("/campaigns/{campaign_id}", response_model=Campaign)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Get a specific campaign with all its details."""
    campaign = crud_campaign.get_with_relations(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=Campaign)
def update_campaign(
    campaign_id: int,
    campaign_in: CampaignUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Update a campaign."""
    campaign = crud_campaign.get(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud_campaign.update_with_relations(db, db_obj=campaign, obj_in=campaign_in)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Delete a campaign."""
    campaign = crud_campaign.get(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud_campaign.remove(db, id=campaign_id)


# ============================================================================
# Campaign Event Endpoints
# ============================================================================

@router.post("/campaigns/{campaign_id}/events", response_model=CampaignEvent, status_code=status.HTTP_201_CREATED)
def create_event(
    campaign_id: int,
    event_in: CampaignEventCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Create a new event in a campaign."""
    campaign = crud_campaign.get(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud_campaign_event.create_for_campaign(db, campaign_id=campaign_id, obj_in=event_in)


@router.get("/events", response_model=List[CampaignEvent])
def list_events(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """List all events (campaign & quick posts) within a date range."""
    return crud_campaign_event.get_events_by_date_range(db, start_date=start_date, end_date=end_date)


@router.put("/events/{event_id}", response_model=CampaignEvent)
def update_event(
    event_id: int,
    event_in: CampaignEventUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Update a campaign event."""
    event = crud_campaign_event.get(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check ownership if linked to campaign
    if event.campaign_id:
        campaign = crud_campaign.get(db, event.campaign_id)
        if campaign and campaign.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    return crud_campaign_event.update(db, db_obj=event, obj_in=event_in)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Delete a campaign event."""
    event = crud_campaign_event.get(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Check ownership if linked to campaign
    if event.campaign_id:
        campaign = crud_campaign.get(db, event.campaign_id)
        if campaign and campaign.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    crud_campaign_event.remove(db, id=event_id)


@router.post("/events/{event_id}/publish")
async def publish_event(
    event_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Publish an event to its configured connector."""
    event = crud_campaign_event.get(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check ownership if linked to campaign
    if event.campaign_id:
        campaign = crud_campaign.get(db, event.campaign_id)
        if campaign and campaign.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    if not event.connector_id:
        raise HTTPException(status_code=400, detail="Event has no connector configured")

    # Get the connector
    connector_model = crud_marketing_connector.get(db, event.connector_id)
    if not connector_model:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Get decrypted credentials and instantiate connector
    config = crud_marketing_connector.get_decrypted_credentials(connector_model)
    connector = get_connector(connector_model.connector_type, config)

    # Build content payload
    content = ContentPayload(
        subject=event.content_subject,
        body=event.content_body or "",
        image_url=event.content_image_url,
        extra=event.content_json or {},
    )

    # Update status to publishing
    crud_campaign_event.update_status(db, event_id=event_id, status="publishing")

    # Publish
    result = await connector.publish(content)

    # Update status based on result
    if result.success:
        crud_campaign_event.update_status(
            db,
            event_id=event_id,
            status="published",
            external_id=result.external_id,
            external_url=result.external_url,
        )
        return {"success": True, "external_id": result.external_id, "external_url": result.external_url}
    else:
        crud_campaign_event.update_status(
            db,
            event_id=event_id,
            status="failed",
            error_message=result.error_message,
        )
        raise HTTPException(status_code=500, detail=result.error_message)


# ============================================================================
# Quick Post Endpoints
# ============================================================================

@router.get("/quick-posts", response_model=List[CampaignEvent])
def list_quick_posts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """List all quick posts (events without a campaign)."""
    return crud_campaign_event.get_quick_posts(db, skip=skip, limit=limit)


@router.post("/quick-posts", response_model=CampaignEvent, status_code=status.HTTP_201_CREATED)
def create_quick_post(
    event_in: CampaignEventCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Create a new quick post."""
    return crud_campaign_event.create_quick_post(db, obj_in=event_in)


# ============================================================================
# Marketing Connector Endpoints
# ============================================================================

@router.get("/connectors", response_model=List[MarketingConnector])
def list_connectors(
    active_only: bool = True,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """List all marketing connectors (user's + store-level)."""
    return crud_marketing_connector.get_by_user(db, user_id=current_user.id, active_only=active_only)


@router.post("/connectors", response_model=MarketingConnector, status_code=status.HTTP_201_CREATED)
def create_connector(
    connector_in: MarketingConnectorCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Create a new marketing connector. Defaults to store-level (shared)."""
    # Use None for user_id to make it store-level/shared
    return crud_marketing_connector.create_with_encryption(db, obj_in=connector_in, user_id=None)


@router.put("/connectors/{connector_id}", response_model=MarketingConnector)
def update_connector(
    connector_id: int,
    connector_in: MarketingConnectorUpdate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Update a marketing connector."""
    connector = crud_marketing_connector.get(db, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    # Allow if owned by user OR if shared (None)
    if connector.user_id is not None and connector.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud_marketing_connector.update(db, db_obj=connector, obj_in=connector_in)


@router.delete("/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Delete a marketing connector."""
    connector = crud_marketing_connector.get(db, connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    if connector.user_id is not None and connector.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud_marketing_connector.remove(db, id=connector_id)


@router.post("/connectors/{connector_id}/test")
async def test_connector(
    connector_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Test a connector's credentials."""
    connector_model = crud_marketing_connector.get(db, connector_id)
    if not connector_model:
        raise HTTPException(status_code=404, detail="Connector not found")
    if connector_model.user_id is not None and connector_model.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    config = crud_marketing_connector.get_decrypted_credentials(connector_model)
    connector = get_connector(connector_model.connector_type, config)
    
    is_valid = await connector.validate_credentials()
    return {"valid": is_valid}


# ============================================================================
# Audience Endpoints
# ============================================================================

@router.get("/audiences", response_model=List[Audience])
def list_audiences(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """List all audiences."""
    return crud_audience.get_by_user(db, user_id=current_user.id)


@router.post("/audiences", response_model=Audience, status_code=status.HTTP_201_CREATED)
def create_audience(
    audience_in: AudienceCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Create a new audience."""
    return crud_audience.create_with_members(db, obj_in=audience_in, user_id=current_user.id)


@router.post("/audiences/{audience_id}/members", response_model=AudienceMember, status_code=status.HTTP_201_CREATED)
def add_audience_member(
    audience_id: int,
    member_in: AudienceMemberCreate,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Add a member to an audience."""
    audience = crud_audience.get(db, audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    if audience.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud_audience.add_member(db, audience_id=audience_id, member_in=member_in)


@router.delete("/audiences/{audience_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_audience_member(
    audience_id: int,
    member_id: int,
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """Remove a member from an audience."""
    audience = crud_audience.get(db, audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    if audience.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not crud_audience.remove_member(db, member_id=member_id):
        raise HTTPException(status_code=404, detail="Member not found")


# ============================================================================
# Smart Boost Recommendations
# ============================================================================

@router.get("/smart-boost", response_model=List[SmartBoostRecommendation])
def get_smart_boost_recommendations(
    db: Session = Depends(dependencies.get_db),
    current_user: models.User = Depends(dependencies.get_current_user),
):
    """
    Get AI-generated campaign recommendations based on inventory and sales data.
    
    This analyzes products for:
    - High stock + Low velocity → Clearance candidates
    - High margin + High velocity → Star products to boost
    - Low stock → Restock alerts (not marketing)
    """
    # Import here to avoid circular imports
    from src.models.product import Product
    from src.models.inventory import InventoryItem
    
    recommendations = []
    
    # Get all products with inventory
    products = (
        db.query(Product)
        .join(InventoryItem)
        .filter(Product.is_bundle.is_(False))
        .all()
    )
    
    for product in products:
        # Calculate metrics
        stock = sum(item.quantity for item in product.inventory_items) if product.inventory_items else 0
        avg_cost = product.average_cost or product.cost_price or 0
        price = product.price or 0
        margin = ((price - avg_cost) / price * 100) if price > 0 else 0
        
        # High stock, low velocity → Clearance
        if stock > 50:  # TODO: Use configurable threshold
            recommendations.append(
                SmartBoostRecommendation(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    reason=f"High stock ({stock} units) - consider clearance promotion",
                    recommended_channels=["email", "social"],
                    suggested_discount_percent=15.0,
                    confidence_score=0.75,
                )
            )
        # High margin → Star product
        elif margin > 40 and stock > 10:
            recommendations.append(
                SmartBoostRecommendation(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    reason=f"High margin ({margin:.1f}%) with good stock - boost visibility",
                    recommended_channels=["paid_ad", "social"],
                    confidence_score=0.85,
                )
            )
    
    return recommendations[:10]  # Limit to top 10 recommendations
