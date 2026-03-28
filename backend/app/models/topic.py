"""Topic model — Display/Video topic targeting performance."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class TopicPerformance(Base):
    __tablename__ = "topic_performance"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)

    topic_id = Column(String(50), nullable=True)
    topic_path = Column(String(500), nullable=True)  # e.g. "Arts & Entertainment > Music"
    bid_modifier = Column(Float, nullable=True)

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    ctr = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", "topic_id", name="uq_topic_perf"),
        Index("idx_topic_date", "date"),
    )

    campaign = relationship("Campaign")
