from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_base_url = Column(String)
    # Default per-order platform-fee rate (fraction, e.g. 0.16 for ML
    # Mexico). The Phase-8 cost engine multiplies revenue by this when
    # the marketplace doesn't return per-order fee data in its API
    # response. Defaults to 0.0 so engine output matches the existing
    # gross-margin report exactly until an operator configures real
    # rates.
    default_fee_rate = Column(Float, nullable=False, default=0.0, server_default="0.0")
    # Default per-order flat shipping cost (paid by seller, in the
    # marketplace's currency). Same fallback semantics as default_fee_rate.
    default_shipping_cost = Column(
        Float, nullable=False, default=0.0, server_default="0.0",
    )

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
    # Set when a refresh attempt fails or no refresh token is available.
    # Cleared on the next successful refresh / re-authorization.
    needs_reauthorization = Column(Boolean, nullable=False, default=False, server_default="false")
    last_refresh_error = Column(String(500), nullable=True)
    # Cursor used by polling workers (e.g. the Amazon order ingestion
    # task) so each run only pulls orders created after the previous
    # successful poll. NULL = no poll has succeeded yet → the worker
    # falls back to the connector's 24h default lookback. Advanced to
    # the wall-clock at the END of a successful poll so a mid-run
    # failure doesn't skip orders on the retry.
    last_orders_polled_at = Column(DateTime(timezone=True), nullable=True)
    # Cursor used by the settlement-fee poller — when set, the next run
    # only re-syncs orders whose breakdown was last touched (or created)
    # after this timestamp. NULL means no settlement sync has succeeded
    # yet → the worker falls back to the connector's default lookback
    # window so a freshly connected credential still backfills.
    last_settlement_synced_at = Column(DateTime(timezone=True), nullable=True)
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
