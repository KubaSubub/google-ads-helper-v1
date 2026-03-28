"""Product Group model — Shopping campaign product hierarchy."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ProductGroup(Base):
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=True)
    google_criterion_id = Column(String(50), nullable=False)

    # Tree structure
    parent_criterion_id = Column(String(50), nullable=True)  # null = root
    case_value_type = Column(String(50), nullable=True)  # PRODUCT_BRAND, PRODUCT_CATEGORY, PRODUCT_TYPE, CUSTOM_LABEL, etc.
    case_value = Column(String(500), nullable=True)  # The actual value (brand name, category path, etc.)
    partition_type = Column(String(20), nullable=True)  # SUBDIVISION or UNIT

    # Bidding
    bid_micros = Column(BigInteger, default=0)
    status = Column(String(20), default="ENABLED")

    # Metrics (aggregated)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    ctr = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "ad_group_id", "google_criterion_id",
                         name="uq_product_group"),
        Index("idx_product_group_campaign", "campaign_id"),
    )

    campaign = relationship("Campaign")
    ad_group = relationship("AdGroup")
