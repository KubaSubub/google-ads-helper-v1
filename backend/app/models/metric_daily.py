"""MetricDaily model for time-series campaign data."""

from sqlalchemy import Column, Integer, BigInteger, Float, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class MetricDaily(Base):
    __tablename__ = "metrics_daily"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # ── Core metrics ──
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)  # Stored as percentage (5.0 = 5%)
    conversions = Column(Float, default=0.0)  # Float — Google Ads returns fractional values
    conversion_value_micros = Column(BigInteger, default=0)  # Revenue in micros
    conversion_rate = Column(Float, default=0.0)
    cost_micros = Column(BigInteger, default=0)
    roas = Column(Float, default=0.0)  # Real ROAS = conversion_value / cost
    avg_cpc_micros = Column(BigInteger, default=0)

    # ── Impression Share (daily campaign level, 0.0-1.0) ──
    search_impression_share = Column(Float, nullable=True)
    search_top_impression_share = Column(Float, nullable=True)
    search_abs_top_impression_share = Column(Float, nullable=True)
    search_budget_lost_is = Column(Float, nullable=True)
    search_budget_lost_top_is = Column(Float, nullable=True)
    search_budget_lost_abs_top_is = Column(Float, nullable=True)
    search_rank_lost_is = Column(Float, nullable=True)
    search_rank_lost_top_is = Column(Float, nullable=True)
    search_rank_lost_abs_top_is = Column(Float, nullable=True)
    search_click_share = Column(Float, nullable=True)

    # ── Extended Conversions ──
    all_conversions = Column(Float, nullable=True)
    all_conversions_value_micros = Column(BigInteger, nullable=True)
    cross_device_conversions = Column(Float, nullable=True)
    value_per_conversion_micros = Column(BigInteger, nullable=True)
    conversions_value_per_cost = Column(Float, nullable=True)  # Google's ROAS

    # ── Top Impression % ──
    abs_top_impression_pct = Column(Float, nullable=True)
    top_impression_pct = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", name="uq_metric_daily"),
        Index("idx_metrics_daily_date", "date"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics_daily")
