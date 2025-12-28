"""
API endpoints for handling webhook notifications from marketplaces.
"""
from typing import Dict
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas import webhook as webhook_schema
from src.models.marketplace import WebhookEvent
from src.crud.crud_marketplace import marketplace as crud_marketplace

router = APIRouter()

@router.post("/mercadolibre")
async def receive_mercadolibre_webhook(
    payload: webhook_schema.MercadoLibreWebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Receives webhook notifications from MercadoLibre.
    
    MercadoLibre sends notifications in this format:
    {
        "resource": "/items/MLM123456789",
        "user_id": 123456789,
        "topic": "items",
        "application_id": 1234567890123456,
        "attempts": 1,
        "sent": "2025-01-01T12:00:00.000Z"
    }
    """
    # Find the marketplace
    db_marketplace = db.query(crud_marketplace.model).filter(
        crud_marketplace.model.name == "MercadoLibre"
    ).first()
    
    if not db_marketplace:
        # Create a default entry if not exists
        db_marketplace = crud_marketplace.model(name="MercadoLibre", api_base_url="https://api.mercadolibre.com")
        db.add(db_marketplace)
        db.commit()
        db.refresh(db_marketplace)
    
    # Log the event
    event = WebhookEvent(
        marketplace_id=db_marketplace.id,
        topic=payload.topic,
        external_resource_id=payload.resource,
        payload=payload.model_dump(),
        status="RECEIVED"
    )
    db.add(event)
    db.commit()
    
    # Schedule background processing
    background_tasks.add_task(process_mercadolibre_event, event.id)
    
    return {"status": "received"}

async def process_mercadolibre_event(event_id: int):
    """
    Background task to process a MercadoLibre webhook event.
    
    This would typically:
    1. Fetch the full resource from MercadoLibre API
    2. Update local data accordingly
    3. Mark the event as processed
    """
    # TODO: Implement full processing logic
    # For now, this is a placeholder
    print(f"Processing MercadoLibre webhook event: {event_id}")

@router.post("/amazon")
async def receive_amazon_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Receives webhook notifications from Amazon SP-API.
    
    Amazon uses EventBridge for notifications. This endpoint would be
    configured as an EventBridge target.
    """
    body = await request.json()
    
    db_marketplace = db.query(crud_marketplace.model).filter(
        crud_marketplace.model.name == "Amazon"
    ).first()
    
    if not db_marketplace:
        db_marketplace = crud_marketplace.model(name="Amazon", api_base_url="https://sellingpartnerapi-na.amazon.com")
        db.add(db_marketplace)
        db.commit()
        db.refresh(db_marketplace)
    
    # Log the event
    event = WebhookEvent(
        marketplace_id=db_marketplace.id,
        topic=body.get("detail-type", "unknown"),
        external_resource_id=body.get("resources", [None])[0],
        payload=body,
        status="RECEIVED"
    )
    db.add(event)
    db.commit()
    
    background_tasks.add_task(process_amazon_event, event.id)
    
    return {"status": "received"}

async def process_amazon_event(event_id: int):
    """
    Background task to process an Amazon webhook event.
    """
    print(f"Processing Amazon webhook event: {event_id}")

@router.get("/events", response_model=list[webhook_schema.WebhookEvent])
def list_webhook_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List recent webhook events for debugging/monitoring.
    """
    events = db.query(WebhookEvent).order_by(WebhookEvent.received_at.desc()).offset(skip).limit(limit).all()
    return events
