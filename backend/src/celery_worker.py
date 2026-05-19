"""
Celery worker configuration.

This module sets up the Celery application instance, configures it with
the Redis broker URL from the application settings, and discovers tasks.
"""
from celery import Celery
from celery.schedules import crontab
from .config import settings

# Create the Celery application instance.
# The first argument is the name of the current module.
# The `broker` argument specifies the URL of the message broker (Redis).
celery_app = Celery(
    "fulcrum",
    broker=settings.REDIS_URL,
    include=["src.tasks"]  # List of modules where tasks are defined
)

# Optional: Configure Celery settings.
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Beat schedule: periodic background polls. Each entry points to a task
# in src/tasks.py. Cadence chosen to balance freshness against SP-API
# rate limits — Amazon allows ~6/min on the Orders endpoint, so polling
# every 15 minutes per credential leaves plenty of headroom even with
# a few credentials.
celery_app.conf.beat_schedule = {
    "amazon-order-poll": {
        "task": "src.tasks.poll_amazon_orders",
        "schedule": crontab(minute="*/15"),
    },
    # ML push webhook is the primary order surface; this poll back-fills
    # the gaps when ML's notifications drop or arrive out of order. Same
    # 15-min cadence as Amazon — ML's rate budget for the per-seller
    # `/orders/search` endpoint is generous enough.
    "mercadolibre-order-poll": {
        "task": "src.tasks.poll_mercadolibre_orders",
        "schedule": crontab(minute="*/15"),
    },
    # ML inbound shipment reconciliation: warehouse receipts move on
    # human/forklift time, not minute-by-minute, so hourly is sufficient.
    # Catches the operator-visible "I sent 100 units to ML Full last week
    # but my dashboard still says 0 received" gap that the manual
    # `receive_items` workflow left.
    "mercadolibre-inbound-reconcile": {
        "task": "src.tasks.reconcile_ml_inbound_shipments",
        "schedule": crontab(minute="10"),  # 10 past every hour
    },
    # Amazon FBA inbound reconciliation: same shape as ML Full, offset
    # 20 minutes so the two reconcilers don't both wake up at the same
    # moment and pile on the marketplace_service DB connection.
    "amazon-inbound-reconcile": {
        "task": "src.tasks.reconcile_amazon_inbound_shipments",
        "schedule": crontab(minute="30"),  # 30 past every hour
    },
    # Alerting (Track 3 Step 6 of 80-advanced-analytics.md). Hourly is
    # the conservative default — most thresholds (margin %, sales dip
    # over 30 days) move slowly. Per-rule cooldowns prevent spam when
    # a condition is sticky.
    "alert-evaluation": {
        "task": "src.tasks.evaluate_alerts",
        "schedule": crontab(minute="5"),  # 5 past every hour
    },
}
