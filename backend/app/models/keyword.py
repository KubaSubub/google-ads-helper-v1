"""Keyword model."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_keyword_id = Column(String(50))
    criterion_kind = Column(String(20), nullable=False, default="POSITIVE")
    text = Column(String(500), nullable=False)
    match_type = Column(String(20))  # EXACT, PHRASE, BROAD
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    serving_status = Column(String(30), nullable=True)  # ELIGIBLE, LOW_SEARCH_VOLUME, BELOW_FIRST_PAGE_BID, RARELY_SERVED
    final_url = Column(String(2000))
    bid_micros = Column(BigInteger, default=0)

    # ── Core metrics (latest sync period) ──
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)  # Float — Google Ads returns fractional values
    conversion_value_micros = Column(BigInteger, default=0)  # Revenue in micros
    ctr = Column(Integer, default=0)  # Stored as micros (e.g., 50000 = 5%)
    avg_cpc_micros = Column(BigInteger, default=0)
    cpa_micros = Column(BigInteger, default=0)  # Cost per acquisition
    quality_score = Column(Integer, default=0)  # Google Ads Quality Score 1-10

    # ── Impression Share (keyword-level, rank-based only, 0.0-1.0) ──
    search_impression_share = Column(Float, nullable=True)
    search_top_impression_share = Column(Float, nullable=True)
    search_abs_top_impression_share = Column(Float, nullable=True)
    search_rank_lost_is = Column(Float, nullable=True)
    search_rank_lost_top_is = Column(Float, nullable=True)
    search_rank_lost_abs_top_is = Column(Float, nullable=True)
    search_exact_match_is = Column(Float, nullable=True)

    # ── Historical Quality Score (enum: BELOW_AVERAGE=1, AVERAGE=2, ABOVE_AVERAGE=3) ──
    historical_quality_score = Column(Integer, nullable=True)
    historical_creative_quality = Column(Integer, nullable=True)
    historical_landing_page_quality = Column(Integer, nullable=True)
    historical_search_predicted_ctr = Column(Integer, nullable=True)

    # ── Extended Conversions ──
    all_conversions = Column(Float, nullable=True)
    all_conversions_value_micros = Column(BigInteger, nullable=True)
    cross_device_conversions = Column(Float, nullable=True)
    value_per_conversion_micros = Column(BigInteger, nullable=True)
    conversions_value_per_cost = Column(Float, nullable=True)  # Google's ROAS

    # ── Top Impression % ──
    abs_top_impression_pct = Column(Float, nullable=True)
    top_impression_pct = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    ad_group = relationship("AdGroup", back_populates="keywords")
    metrics_daily = relationship("KeywordDaily", back_populates="keyword", cascade="all, delete-orphan")
