"""
Payment model — tracks the linkage between a Fulcrum SalesOrder and a
gateway-side payment. Today's only gateway is Mercado Pago; the
`provider` column is keyed for easy extension (e.g. Stripe, PayPal) so
the rest of the schema doesn't need to change when a second gateway
ships.
"""
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class PaymentStatus(str, enum.Enum):
    """Canonical payment lifecycle states.

    Mercado Pago publishes ~10 statuses (pending, approved, authorized,
    in_process, in_mediation, rejected, cancelled, refunded,
    charged_back, partially_refunded). The connector maps them down to
    these five so callers don't have to know each provider's vocabulary.
    """
    PENDING = "pending"      # in_process / pending / authorized / in_mediation
    APPROVED = "approved"    # approved
    REJECTED = "rejected"    # rejected
    REFUNDED = "refunded"    # refunded / partially_refunded / charged_back
    CANCELLED = "cancelled"  # cancelled

    @classmethod
    def from_mercado_pago(cls, mp_status: str) -> "PaymentStatus":
        m = (mp_status or "").lower()
        if m == "approved":
            return cls.APPROVED
        if m == "rejected":
            return cls.REJECTED
        if m in ("refunded", "charged_back", "partially_refunded"):
            return cls.REFUNDED
        if m == "cancelled":
            return cls.CANCELLED
        # pending, in_process, authorized, in_mediation, anything unknown
        return cls.PENDING


class Payment(Base):
    """One row per attempted payment.

    Unique on (provider, external_payment_id) so re-receiving the same
    webhook only updates the existing row instead of creating a duplicate.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    sales_order_id = Column(
        Integer,
        ForeignKey("sales_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    provider = Column(String(32), nullable=False, default="mercado_pago", index=True)
    # Provider's payment id (e.g. MP payment_id). NULL if the create
    # call failed before MP returned an id — we still keep the row so
    # the retry path has somewhere to land.
    external_payment_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default=PaymentStatus.PENDING.value, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="MXN")
    # Cardholder email, snapshotted at create time. Useful for refunds /
    # support when the SalesOrder has no email of its own.
    payer_email = Column(String(255), nullable=True)
    # Raw provider response body, kept for audit and to surface error
    # details on the Payments page without re-hitting MP.
    raw_response = Column(JSON, nullable=True)
    # The most recent webhook event payload. Helps debug a payment whose
    # status changed without an obvious cause (e.g. chargeback weeks
    # after capture).
    last_webhook_payload = Column(JSON, nullable=True)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sales_order = relationship("SalesOrder")
    user = relationship("User")
