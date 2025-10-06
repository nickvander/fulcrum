"""
Celery worker configuration.

This module sets up the Celery application instance, configures it with
the Redis broker URL from the application settings, and discovers tasks.
"""
from celery import Celery
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
