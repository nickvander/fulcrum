from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

# --- Webhook Subscription Schemas ---

class WebhookSubscriptionBase(BaseModel):
    marketplace_id: int
    topic: str  # e.g., "orders", "items", "questions"
    callback_url: str

class WebhookSubscriptionCreate(WebhookSubscriptionBase):
    pass

class WebhookSubscriptionUpdate(BaseModel):
    topic: Optional[str] = None
    callback_url: Optional[str] = None
    status: Optional[str] = None

class WebhookSubscription(WebhookSubscriptionBase):
    id: int
    user_id: int
    external_subscription_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- Webhook Event Schemas ---

class WebhookEventBase(BaseModel):
    marketplace_id: int
    topic: str
    external_resource_id: Optional[str] = None
    payload: Dict[str, Any]

class WebhookEventCreate(WebhookEventBase):
    pass

class WebhookEvent(WebhookEventBase):
    id: int
    status: str
    error_message: Optional[str] = None
    received_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- Incoming Webhook Payload (MercadoLibre format) ---

class MercadoLibreWebhookPayload(BaseModel):
    """
    Standard MercadoLibre webhook notification format.
    """
    _id: Optional[str] = None
    resource: str  # e.g., "/items/MLM123456789"
    user_id: int
    topic: str  # e.g., "items", "orders", "questions"
    application_id: int
    attempts: int
    sent: datetime
    received: Optional[datetime] = None
