"""MetricDaily model for time-series campaign data."""

from sqlalchemy import Column, Integer, BigInteger, Float, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class MetricDaily(Base):
    __tablename__ = "metrics_daily"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    cost_micros = Column(BigInteger, default=0)
    roas = Column(Float, default=0.0)
    avg_cpc_micros = Column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", name="uq_metric_daily"),
        Index("idx_metrics_daily_date", "date"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics_daily")
