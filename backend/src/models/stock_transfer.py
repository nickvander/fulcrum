from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base


class StockTransferStatus(str, enum.Enum):
    DRAFT = "draft"
    SHIPPED = "shipped"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


# Convention: well-known stock location identifiers (free-form strings on
# InventoryItem.location). Promoted to a real table in a later slice.
LOCATION_INTERNAL = "default"
LOCATION_ML_FULL = "ml-full"
LOCATION_AMAZON_FBA = "amazon-fba"


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)
    source_location = Column(String, nullable=False, default=LOCATION_INTERNAL)
    dest_location = Column(String, nullable=False)
    status = Column(String, nullable=False, default=StockTransferStatus.DRAFT.value)
    notes = Column(String, nullable=True)

    # For Slice 2: external inbound shipment id from MercadoLibre / Amazon
    external_inbound_id = Column(String, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship(
        "StockTransferItem",
        back_populates="transfer",
        cascade="all, delete-orphan",
    )
    created_by = relationship("User", foreign_keys=[created_by_id])


class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    qty_planned = Column(Integer, nullable=False, default=0)
    qty_shipped = Column(Integer, nullable=False, default=0)
    qty_received = Column(Integer, nullable=False, default=0)

    transfer = relationship("StockTransfer", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
