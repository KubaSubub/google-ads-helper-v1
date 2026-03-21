"""Campaign-level assets (extensions) -- sitelinks, callouts, snippets, etc."""

from sqlalchemy import Column, Integer, Float, BigInteger, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class CampaignAsset(Base):
    __tablename__ = "campaign_assets"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    google_asset_id = Column(String(50), nullable=False)
    asset_type = Column(String(30), nullable=False)
    asset_name = Column(String(500), nullable=True)
    asset_detail = Column(String(2000), nullable=True)
    status = Column(String(20), nullable=True)
    performance_label = Column(String(20), nullable=True)
    source = Column(String(20), nullable=True)

    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "google_asset_id", "asset_type",
                         name="uq_campaign_asset"),
        Index("idx_campaign_asset_type", "asset_type"),
    )

    campaign = relationship("Campaign")
