from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_base_url = Column(String)

class MarketplaceCredential(Base):
    __tablename__ = "marketplace_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    access_token = Column(String)  # Encrypted
    refresh_token = Column(String)  # Encrypted
    token_type = Column(String, nullable=True)
    scopes = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    marketplace = relationship("Marketplace")

class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    external_listing_id = Column(String)
    listing_url = Column(String)
    status = Column(String)
    sync_status = Column(String, default="PENDING")
    last_sync = Column(DateTime(timezone=True), onupdate=func.now())
    marketplace_price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    discount_percentage = Column(Float, nullable=True)
    available_quantity = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True) # Renamed to avoid reserved word 'metadata'

    product = relationship("Product", back_populates="marketplace_listings")
    marketplace = relationship("Marketplace")

class WebhookSubscription(Base):
    """
    Stores webhook subscriptions for marketplace notifications.
    """
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)  # e.g., "orders", "items", "questions"
    callback_url = Column(String)
    external_subscription_id = Column(String, nullable=True)  # ID from marketplace
    status = Column(String, default="ACTIVE")
    secret = Column(String, nullable=True)  # For signature verification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    marketplace = relationship("Marketplace")
    user = relationship("User")

class WebhookEvent(Base):
    """
    Logs incoming webhook events for auditing and retry.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    topic = Column(String, index=True)
    external_resource_id = Column(String, nullable=True)
    payload = Column(JSON)
    status = Column(String, default="RECEIVED")  # RECEIVED, PROCESSED, FAILED
    error_message = Column(String, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    marketplace = relationship("Marketplace")


class MarketplaceAppCredential(Base):
    """
    Stores developer/app credentials (client_id, client_secret) for each marketplace.
    These are the app credentials used to initiate OAuth flows.
    Different from MarketplaceCredential which stores access/refresh tokens.
    """
    __tablename__ = "marketplace_app_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    client_id = Column(String, nullable=False)
    client_secret_encrypted = Column(String, nullable=False)  # Encrypted
    redirect_uri = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    marketplace = relationship("Marketplace")
