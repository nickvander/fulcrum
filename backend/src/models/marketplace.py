from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship

from .base import Base

class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_base_url = Column(String)

class MarketplaceCredentials(Base):
    __tablename__ = "marketplace_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id"))
    access_token = Column(String) # Encrypted
    refresh_token = Column(String) # Encrypted
    expires_at = Column(TIMESTAMP)

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

    product = relationship("Product", back_populates="marketplace_listings")
    marketplace = relationship("Marketplace")
