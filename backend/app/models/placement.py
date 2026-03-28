"""Placement model — Display/Video managed and automatic placements."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Placement(Base):
    __tablename__ = "placements"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)

    # Placement info
    placement_url = Column(String(2000), nullable=True)  # Website URL, YouTube channel, app
    placement_type = Column(String(30), nullable=True)    # WEBSITE, YOUTUBE_CHANNEL, YOUTUBE_VIDEO, MOBILE_APP
    display_name = Column(String(500), nullable=True)

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    ctr = Column(Float, default=0.0)
    avg_cpc_micros = Column(BigInteger, default=0)

    # Video-specific metrics (nullable — only for Video campaigns)
    video_views = Column(Integer, nullable=True)
    video_view_rate = Column(Float, nullable=True)  # Percentage
    avg_cpv_micros = Column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", "placement_url",
                         name="uq_placement_campaign_date_url"),
        Index("idx_placement_date", "date"),
        Index("idx_placement_type", "placement_type"),
    )

    campaign = relationship("Campaign")
