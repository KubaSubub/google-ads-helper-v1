"""Keyword model."""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_keyword_id = Column(String(50))
    text = Column(String(500), nullable=False)
    match_type = Column(String(20))  # EXACT, PHRASE, BROAD
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    final_url = Column(String(2000))
    bid_micros = Column(BigInteger, default=0)

    # Aggregated metrics (latest sync period)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Integer, default=0)
    ctr = Column(Integer, default=0)  # Stored as micros (e.g., 50000 = 5%)
    avg_cpc_micros = Column(BigInteger, default=0)
    cpa_micros = Column(BigInteger, default=0)  # Cost per acquisition
    quality_score = Column(Integer, default=0)  # Google Ads Quality Score 1-10

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    ad_group = relationship("AdGroup", back_populates="keywords")
