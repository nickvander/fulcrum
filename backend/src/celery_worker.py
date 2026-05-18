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
    # Alerting (Track 3 Step 6 of 80-advanced-analytics.md). Hourly is
    # the conservative default — most thresholds (margin %, sales dip
    # over 30 days) move slowly. Per-rule cooldowns prevent spam when
    # a condition is sticky.
    "alert-evaluation": {
        "task": "src.tasks.evaluate_alerts",
        "schedule": crontab(minute="5"),  # 5 past every hour
    },
}
