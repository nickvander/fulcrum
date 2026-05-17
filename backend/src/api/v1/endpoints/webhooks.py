"""
API endpoints for handling webhook notifications from marketplaces.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session

from src.database import SessionLocal, get_db
from src.schemas import webhook as webhook_schema
from src.models.marketplace import (
    MarketplaceCredential,
    MarketplaceListing,
    WebhookEvent,
)
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.crud.crud_marketplace import marketplace as crud_marketplace

logger = logging.getLogger(__name__)

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

def _extract_external_id(resource: Optional[str]) -> Optional[str]:
    """ML sends `resource` like `/orders/1234567` or `/items/MLM123`. Return the trailing id."""
    if not resource:
        return None
    parts = [p for p in resource.split("/") if p]
    return parts[-1] if parts else None


def _ml_order_to_sales_order(payload: Dict[str, Any]) -> SalesOrder:
    status = (payload.get("status") or "PENDING").upper()
    total_amount = payload.get("total_amount") or payload.get("paid_amount")
    date_created = payload.get("date_created")
    created_at: Optional[datetime] = None
    if isinstance(date_created, str):
        try:
            parsed = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
            # SalesOrder.created_at is a naive TIMESTAMP — strip tz and normalize to UTC.
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            created_at = parsed
        except ValueError:
            created_at = None

    return SalesOrder(
        status=status,
        total_price=float(total_amount) if total_amount is not None else None,
        created_at=created_at or datetime.utcnow(),
        source=OrderSource.MERCADOLIBRE,
        external_order_id=str(payload.get("id")) if payload.get("id") is not None else None,
    )


def _find_local_product_id(db: Session, marketplace_id: int, item_payload: Dict[str, Any]) -> Optional[int]:
    """Resolve a ML order line item to a local Fulcrum product via marketplace_listings."""
    external_id = item_payload.get("id") or item_payload.get("item_id")
    if not external_id:
        return None
    listing = (
        db.query(MarketplaceListing)
        .filter(
            MarketplaceListing.marketplace_id == marketplace_id,
            MarketplaceListing.external_listing_id == str(external_id),
        )
        .first()
    )
    return listing.product_id if listing else None


async def process_mercadolibre_event(event_id: int):
    """
    Background task to process a MercadoLibre webhook event.

    Flow for `orders` / `orders_v2` topics:
    1. Load the event and resolve the topic + external resource id.
    2. Pick any MarketplaceCredential for the ML marketplace (webhook does not carry user context).
    3. Fetch the order detail via the ML connector.
    4. Upsert a SalesOrder + SalesOrderItems keyed by external_order_id.
    5. Decrement Fulcrum stock for each matched product (ML Full handles fulfillment, but the stock
       reservation is still reflected locally so dashboards stay accurate).
    6. Mark the WebhookEvent as PROCESSED (or FAILED with error_message).

    For non-order topics we just mark PROCESSED — items/questions/etc. are no-ops for now.
    """
    # Use a fresh session — get_db() is request-scoped; background tasks need their own.
    from src.services.marketplace_service import marketplace_service
    from src.services.inventory_service import InventoryService

    db: Session = SessionLocal()
    try:
        event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        if not event:
            logger.warning("Webhook event %s not found", event_id)
            return

        try:
            topic = (event.topic or "").lower()
            if topic not in {"orders", "orders_v2", "created_orders"}:
                event.status = "PROCESSED"
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
                return

            external_order_id = _extract_external_id(event.external_resource_id)
            if not external_order_id:
                event.status = "FAILED"
                event.error_message = "Could not parse order id from resource"
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
                return

            # Defensive guard against the multi-tenant bug documented as item 8
            # in 87-sales-orders-cherry-handoff.md. ML webhooks carry NO user
            # identifier — just `resource: /orders/<id>`. If more than one user
            # has connected their own ML credentials to this marketplace, we
            # have no reliable way to pick which one is the correct one to
            # authenticate as. The most-recently-updated heuristic worked when
            # Fulcrum was strictly single-tenant, but in a multi-tenant setup
            # it would silently fetch User A's order using User B's
            # credentials → either a 404/forbidden (best case) or successful
            # access against the wrong account's data (worst case).
            #
            # Until we add per-user webhook URLs (option 1 in the handoff) or
            # seller-id-based lookup (option 2), refuse the event when we
            # detect more than one credential. The webhook caller (ML) will
            # see a 200 from the POST handler — only the background task
            # marks the event FAILED with a clear reason so the next operator
            # to look at WebhookEvent.status sees why nothing happened.
            credential_q = (
                db.query(MarketplaceCredential)
                .filter(MarketplaceCredential.marketplace_id == event.marketplace_id)
                .order_by(MarketplaceCredential.updated_at.desc().nullslast(), MarketplaceCredential.id.desc())
            )
            credential_count = credential_q.count()
            credential = credential_q.first()
            if not credential:
                event.status = "FAILED"
                event.error_message = "No marketplace credential available to fetch order"
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
                return
            if credential_count > 1:
                event.status = "FAILED"
                event.error_message = (
                    f"Multi-tenant credentials detected ({credential_count} for marketplace "
                    f"{event.marketplace_id}); ML webhooks carry no user context, so we "
                    "cannot determine which credential owns this order. See item 8 in "
                    "work/future/87-sales-orders-cherry-handoff.md for the fix options."
                )
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
                logger.warning(
                    "Refusing ML webhook event %s: %d credentials for marketplace %s",
                    event.id, credential_count, event.marketplace_id,
                )
                return

            access_token = await marketplace_service.get_valid_access_token(db, credential.id)
            connector = marketplace_service.get_connector("MercadoLibre")
            order_payload = await connector.fetch_order(external_order_id, access_token)

            existing = (
                db.query(SalesOrder)
                .filter(
                    SalesOrder.source == OrderSource.MERCADOLIBRE,
                    SalesOrder.external_order_id == external_order_id,
                )
                .first()
            )
            if existing:
                # Update status/total but don't re-decrement stock for the same order.
                ml_order = _ml_order_to_sales_order(order_payload)
                existing.status = ml_order.status
                existing.total_price = ml_order.total_price
                db.commit()
                event.status = "PROCESSED"
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
                return

            sales_order = _ml_order_to_sales_order(order_payload)
            db.add(sales_order)
            db.flush()

            inventory_service = InventoryService()
            for line in order_payload.get("order_items", []) or []:
                item_payload = line.get("item") or {}
                quantity = int(line.get("quantity") or 0)
                unit_price = line.get("unit_price")
                product_id = _find_local_product_id(db, event.marketplace_id, item_payload)

                db.add(
                    SalesOrderItem(
                        order_id=sales_order.id,
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=float(unit_price) if unit_price is not None else None,
                    )
                )

                if product_id and quantity > 0:
                    inventory_service.adjust_stock(
                        db,
                        product_id=product_id,
                        adjustment=-quantity,
                        reason=f"MercadoLibre order {external_order_id}",
                        user_id="mercadolibre-webhook",
                    )

            event.status = "PROCESSED"
            event.processed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # noqa: BLE001 — we want any failure to mark the event
            logger.exception("Failed to process MercadoLibre webhook %s", event_id)
            db.rollback()
            # Re-fetch event because rollback expires it
            event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
            if event:
                event.status = "FAILED"
                event.error_message = str(exc)[:500]
                event.processed_at = datetime.now(timezone.utc)
                db.commit()
    finally:
        db.close()

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
