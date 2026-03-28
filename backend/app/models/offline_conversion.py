"""Offline Conversion model — GCLID-based offline conversion uploads."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class OfflineConversion(Base):
    __tablename__ = "offline_conversions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    gclid = Column(String(200), nullable=False)
    conversion_action_id = Column(String(50), nullable=True)
    conversion_name = Column(String(200), nullable=True)
    conversion_time = Column(DateTime, nullable=False)
    conversion_value_micros = Column(BigInteger, nullable=True)
    currency_code = Column(String(10), default="PLN")

    # Upload status
    upload_status = Column(String(20), default="PENDING")  # PENDING, UPLOADED, FAILED
    error_message = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        UniqueConstraint("client_id", "gclid", "conversion_time", name="uq_offline_conversion"),
    )

    client = relationship("Client")
