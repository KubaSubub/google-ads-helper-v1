"""MetricSegmented model for device + geo breakdowns of campaign metrics."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class MetricSegmented(Base):
    __tablename__ = "metrics_segmented"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Segment dimensions (one or more may be populated)
    device = Column(String(20), nullable=True)    # MOBILE, DESKTOP, TABLET, OTHER
    geo_city = Column(String(200), nullable=True)  # City name (resolved from resource name)
    hour_of_day = Column(Integer, nullable=True)  # 0-23 for hourly dayparting
    # GAP 4A: Demographic segments
    age_range = Column(String(30), nullable=True)  # AGE_RANGE_18_24, AGE_RANGE_25_34, etc.
    gender = Column(String(20), nullable=True)     # MALE, FEMALE, UNDETERMINED
    ad_network_type = Column(String(30), nullable=True)

    # Core metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)  # Percentage (5.0 = 5%)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    cost_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)

    # Impression share (available at campaign+segment level)
    search_impression_share = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", "device", "geo_city", "hour_of_day", "age_range", "gender", name="uq_metric_segmented"),
        Index("idx_metrics_segmented_date", "date"),
        Index("idx_metrics_segmented_device", "device"),
        Index("idx_metrics_segmented_geo", "geo_city"),
        Index("idx_metrics_segmented_age", "age_range"),
        Index("idx_metrics_segmented_gender", "gender"),
        Index("idx_metrics_segmented_network", "ad_network_type"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics_segmented")
