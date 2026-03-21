"""Campaign audience metrics from campaign_audience_view."""

from sqlalchemy import Column, Integer, Float, BigInteger, String, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class CampaignAudienceMetric(Base):
    __tablename__ = "campaign_audience_metrics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    audience_resource_name = Column(String(500), nullable=False)
    audience_name = Column(String(500), nullable=True)
    audience_type = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)

    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    cost_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)

    bid_modifier = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "audience_resource_name", "date",
                         name="uq_campaign_audience_metric"),
        Index("idx_campaign_audience_date", "date"),
        Index("idx_campaign_audience_type", "audience_type"),
    )

    campaign = relationship("Campaign")
