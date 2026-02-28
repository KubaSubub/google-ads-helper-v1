"""Campaign model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    google_campaign_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    campaign_type = Column(String(50))  # SEARCH, DISPLAY, SHOPPING, etc.
    budget_micros = Column(BigInteger, default=0)  # 1 USD = 1_000_000 micros
    budget_type = Column(String(20))  # DAILY, TOTAL
    bidding_strategy = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)

    # ── Impression Share (campaign-level, 0.0-1.0 from API) ──
    search_impression_share = Column(Float, nullable=True)
    search_top_impression_share = Column(Float, nullable=True)
    search_abs_top_impression_share = Column(Float, nullable=True)
    # Budget-lost IS (campaign-level ONLY)
    search_budget_lost_is = Column(Float, nullable=True)
    search_budget_lost_top_is = Column(Float, nullable=True)
    search_budget_lost_abs_top_is = Column(Float, nullable=True)
    # Rank-lost IS
    search_rank_lost_is = Column(Float, nullable=True)
    search_rank_lost_top_is = Column(Float, nullable=True)
    search_rank_lost_abs_top_is = Column(Float, nullable=True)
    # Click share & exact match IS
    search_click_share = Column(Float, nullable=True)
    search_exact_match_is = Column(Float, nullable=True)

    # ── Top Impression % ──
    abs_top_impression_pct = Column(Float, nullable=True)
    top_impression_pct = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("client_id", "google_campaign_id", name="uq_campaign_google_id"),
    )

    # Relationships
    client = relationship("Client", back_populates="campaigns")
    ad_groups = relationship("AdGroup", back_populates="campaign", cascade="all, delete-orphan")
    metrics_daily = relationship("MetricDaily", back_populates="campaign", cascade="all, delete-orphan")
    metrics_segmented = relationship("MetricSegmented", back_populates="campaign", cascade="all, delete-orphan")
    search_terms = relationship("SearchTerm", back_populates="campaign", cascade="all, delete-orphan")
