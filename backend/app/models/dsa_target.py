"""DsaTarget model — Dynamic Search Ads targeting criteria with performance."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DsaTarget(Base):
    __tablename__ = "dsa_targets"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(50))  # PAGE_FEED, URL_CONTAINS, CATEGORY, ALL_WEBPAGES
    target_value = Column(String(500))
    status = Column(String(20), default="ENABLED")
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign")
