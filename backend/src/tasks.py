"""
Celery tasks for the Fulcrum application.

This module contains the definitions for background tasks that are executed
asynchronously by the Celery worker.
"""
import logging

from .celery_worker import celery_app
from src.database import SessionLocal
from src.crud import crud_product
from src.services.dummy_ai_service import ai_service

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.evaluate_alerts")
def evaluate_alerts():
    """
    Periodic alert evaluator. Scheduled hourly by celery beat
    (`src/celery_worker.py::celery_app.conf.beat_schedule`).

    Each tick:
      - Iterates every enabled AlertRule across all users.
      - Runs the type-specific evaluator (low_margin / sales_dip /
        stockout_risk) against the same SQL helpers the dashboard
        reports use.
      - For triggered rules outside their cooldown window: composes
        an email via the existing EmailService, inserts an AlertEvent
        row, and advances `last_triggered_at`.

    Returns the batch summary {rules_evaluated, rules_triggered,
    notifications_sent, rule_results}. Beat ignores the return value;
    operators can call `.delay()` and inspect for ad-hoc debugging.
    """
    from src.services.alert_evaluation_service import evaluate_all_enabled_rules

    db = SessionLocal()
    try:
        result = evaluate_all_enabled_rules(db)
        return result.model_dump()
    finally:
        db.close()


@celery_app.task(name="src.tasks.poll_amazon_orders")
def poll_amazon_orders():
    """
    Periodic Amazon order ingestion. Scheduled by celery beat
    (`src/celery_worker.py::celery_app.conf.beat_schedule`).

    Each tick:
      - Iterates every healthy Amazon MarketplaceCredential
        (`needs_reauthorization=False`, tokens present).
      - Pulls orders since the credential's `last_orders_polled_at`
        cursor via SP-API.
      - Upserts SalesOrder + SalesOrderItem rows, decrementing local
        stock on new orders.
      - Advances the cursor only when the per-credential work commits.

    Returns a {credential_id: summary} dict so a one-off `.delay()`
    call from a test or operator inspection has something readable to
    look at. Beat itself ignores the return value.
    """
    from src.services.amazon_order_ingestion import poll_all_amazon_credentials

    db = SessionLocal()
    try:
        return poll_all_amazon_credentials(db)
    finally:
        db.close()


@celery_app.task(name="src.tasks.backfill_order_cost_breakdowns")
def backfill_order_cost_breakdowns():
    """
    Phase-8 cost-engine backfill. Scheduled by celery beat
    (`src/celery_worker.py::celery_app.conf.beat_schedule`).

    The ingestion paths (Amazon poll, ML poll, ML webhook) already
    call `upsert_breakdown_safe` after each new order, so 99% of
    new orders are populated immediately. This task catches:

      - Orders ingested before the cost engine landed.
      - Orders whose post-ingest upsert failed (logged + swallowed
        in the ingestion path so the order itself isn't blocked).
      - Future operator action: changing `Marketplace.default_fee_rate`
        — though that needs an explicit "recompute all" trigger, not
        just this `only_missing` pass. Wire that when fee-config UI
        lands.

    Returns a {created, updated, errors} summary for ad-hoc
    inspection. Beat ignores the return value.
    """
    from src.services.order_cost_engine import recompute_for_orders

    db = SessionLocal()
    try:
        return recompute_for_orders(db, only_missing=True, limit=500)
    finally:
        db.close()


@celery_app.task(name="src.tasks.reconcile_amazon_inbound_shipments")
def reconcile_amazon_inbound_shipments():
    """
    Periodic Amazon FBA inbound-shipment reconciliation. Scheduled by
    celery beat (`src/celery_worker.py::celery_app.conf.beat_schedule`).

    Mirrors `reconcile_ml_inbound_shipments` against the Amazon FBA
    inbound API (`AmazonConnector.get_inbound_shipment_status`). Iterates
    every StockTransfer in SHIPPED / PARTIALLY_RECEIVED with
    `dest_location='amazon-fba'` and a non-NULL `external_inbound_id`.

    Returns a {transfer_id: summary} dict for ad-hoc inspection.
    """
    from src.services.inbound_shipment_reconciliation import (
        reconcile_all_open_amazon_inbounds,
    )

    db = SessionLocal()
    try:
        return reconcile_all_open_amazon_inbounds(db)
    finally:
        db.close()


@celery_app.task(name="src.tasks.reconcile_ml_inbound_shipments")
def reconcile_ml_inbound_shipments():
    """
    Periodic ML Full inbound-shipment reconciliation. Scheduled by
    celery beat (`src/celery_worker.py::celery_app.conf.beat_schedule`).

    Each tick:
      - Iterates every StockTransfer in SHIPPED or PARTIALLY_RECEIVED
        with a non-NULL `external_inbound_id` and `dest_location=ml-full`.
      - Calls ML's inbound-shipment status endpoint for each.
      - Applies any positive delta between the marketplace's reported
        received quantity and the local `qty_received` — credits stock
        at the `ml-full` location and advances the transfer status to
        PARTIALLY_RECEIVED / RECEIVED.

    Returns a {transfer_id: summary} dict for ad-hoc inspection.
    """
    from src.services.inbound_shipment_reconciliation import (
        reconcile_all_open_ml_inbounds,
    )

    db = SessionLocal()
    try:
        return reconcile_all_open_ml_inbounds(db)
    finally:
        db.close()


@celery_app.task(name="src.tasks.poll_mercadolibre_orders")
def poll_mercadolibre_orders():
    """
    Periodic MercadoLibre order back-fill. The primary order surface
    is the ML push webhook (`api/v1/endpoints/webhooks.py`); this poll
    catches anything the webhook missed (ML's notification delivery is
    best-effort and occasionally drops or arrives out of order).

    Same shape as `poll_amazon_orders`: per-credential SAVEPOINT,
    upsert by `(source, external_order_id)`, decrement stock only on
    inserts. Cursor lives on `MarketplaceCredential.last_orders_polled_at`.

    Returns a {credential_id: summary} dict for ad-hoc inspection.
    """
    from src.services.mercadolibre_order_ingestion import (
        poll_all_mercadolibre_credentials,
    )

    db = SessionLocal()
    try:
        return poll_all_mercadolibre_credentials(db)
    finally:
        db.close()


@celery_app.task
def generate_product_embedding(product_id: int):
    """
    Generates and saves a vector embedding for a product using the AI service.
    """
    db = SessionLocal()
    try:
        product = crud_product.product.get(db, id=product_id)
        if not product:
            print(f"Product with ID {product_id} not found.")
            return

        # In a real app, you might combine more fields
        text_to_embed = f"{product.name} {product.description}"
        embedding = ai_service.generate_embedding(text_to_embed)

        # Update the product with the new embedding
        crud_product.product.update(db, db_obj=product, obj_in={"embedding": embedding})
        print(f"Successfully generated and saved embedding for product ID: {product_id}")
    finally:
        db.close()

    return {"product_id": product_id, "status": "success"}
