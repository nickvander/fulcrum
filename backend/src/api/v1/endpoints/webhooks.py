"""
API endpoints for handling webhook notifications from marketplaces.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session

from src.core.errors import LocalizedHTTPException
from src.database import SessionLocal, get_db
from src.schemas import webhook as webhook_schema
from src.models.marketplace import (
    MarketplaceCredential,
    WebhookEvent,
)
from src.models.order import OrderSource, SalesOrder, SalesOrderItem
from src.crud.crud_marketplace import marketplace as crud_marketplace

# Helpers `_ml_order_to_sales_order` and `_find_local_product_id`
# live in `services/mercadolibre_order_ingestion.py` so the poller
# and the webhook share one implementation. Aliased here for any
# external import that still references the private name.
from src.services.mercadolibre_order_ingestion import (
    find_local_product_id as _find_local_product_id,
    ml_order_to_sales_order as _ml_order_to_sales_order,
)

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

                # Capture cost-at-sale so the margin report stops drifting
                # when Product.cost_price is later changed. NULL when the
                # line item isn't mapped to a Fulcrum product (cost
                # unknowable); the margin SQL falls back to product cost
                # via COALESCE for legacy rows so this is safe.
                cost_per_unit = None
                if product_id is not None:
                    from src.models.product import Product
                    product = db.query(Product).filter(Product.id == product_id).first()
                    if product and product.cost_price is not None:
                        cost_per_unit = float(product.cost_price)

                db.add(
                    SalesOrderItem(
                        order_id=sales_order.id,
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=float(unit_price) if unit_price is not None else None,
                        cost_per_unit=cost_per_unit,
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


# ---------------------------------------------------------------------------
# Mercado Pago payment webhooks
#
# MP sends notifications shaped roughly:
#   {
#     "type": "payment",
#     "action": "payment.updated",
#     "data": { "id": "1234567890" },
#     ...
#   }
# We verify the `x-signature` header against MERCADOPAGO_WEBHOOK_SECRET,
# fetch the canonical payment from MP, and update the matching `Payment`
# row by `external_payment_id`. Same idempotency semantics as the ML
# webhook — re-receiving the same notification just refreshes status.
# ---------------------------------------------------------------------------


@router.post("/mercadopago")
async def receive_mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from src.config import settings as _settings
    from src.services.mercado_pago import mercado_pago_connector

    raw_body = await request.body()
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — some MP test webhooks send empty body
        body = {}

    headers = request.headers
    signature_ok = mercado_pago_connector.verify_webhook_signature(
        signature_header=headers.get("x-signature"),
        request_id_header=headers.get("x-request-id"),
        data_id=(body.get("data") or {}).get("id") if isinstance(body, dict) else None,
        secret=_settings.MERCADOPAGO_WEBHOOK_SECRET,
    )
    if not signature_ok:
        logger.warning("Rejecting MercadoPago webhook — invalid signature")
        raise LocalizedHTTPException(
            status_code=401,
            code="apiErrors.payments.invalidWebhookSignature",
            detail="Invalid MercadoPago webhook signature",
        )

    # MP retries on non-2xx, so we acknowledge fast and process in the
    # background. The same pattern the ML webhook uses.
    background_tasks.add_task(
        _process_mercadopago_event,
        body if isinstance(body, dict) else {"raw": raw_body.decode("utf-8", errors="replace")},
    )
    return {"status": "received"}


async def _process_mercadopago_event(payload: Dict[str, Any]) -> None:
    """Background task: fetch the canonical payment from MP, update
    the matching Payment row by external_payment_id. Tolerates a
    missing payment (e.g. the create-payment call hasn't returned yet
    — MP can deliver a webhook before the synchronous response on a
    fast network)."""
    from src.crud import crud_payment as _crud_payment
    from src.models.payment import PaymentStatus
    from src.services.mercado_pago import mercado_pago_connector

    event_type = (payload.get("type") or "").lower()
    if event_type and event_type != "payment":
        # Future MP event types (chargebacks, plans, subscriptions)
        # land here but aren't payment notifications; ignore quietly.
        return

    data_id = (payload.get("data") or {}).get("id") if isinstance(payload, dict) else None
    if not data_id:
        return

    result = await mercado_pago_connector.fetch_payment(str(data_id))
    db: Session = SessionLocal()
    try:
        payment = _crud_payment.get_by_provider_id(
            db, provider="mercado_pago", external_payment_id=str(data_id),
        )
        if payment is None:
            logger.info(
                "MercadoPago webhook for unknown payment id=%s — ignoring "
                "(the create-payment call may still be in flight)", data_id,
            )
            return
        new_status = PaymentStatus.from_mercado_pago(result.status)
        _crud_payment.apply_webhook(
            db, payment=payment, status=new_status, payload=result.raw or payload,
        )
        db.commit()
    finally:
        db.close()
