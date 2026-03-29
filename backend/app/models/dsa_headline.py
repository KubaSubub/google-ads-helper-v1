"""DsaHeadline model — Dynamic Search Ads auto-generated headlines with performance."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DsaHeadline(Base):
    __tablename__ = "dsa_headlines"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    search_term_text = Column(String(500))
    generated_headline = Column(String(200))
    landing_page_url = Column(String(1000))
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0)
    date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign")
