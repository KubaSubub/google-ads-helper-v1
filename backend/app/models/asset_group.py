"""Asset Group model for PMax campaigns."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    google_asset_group_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    status = Column(String(20))
    ad_strength = Column(String(20), nullable=True)
    final_url = Column(String(2000), nullable=True)
    final_mobile_url = Column(String(2000), nullable=True)
    path1 = Column(String(100), nullable=True)
    path2 = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("campaign_id", "google_asset_group_id", name="uq_asset_group"),
    )

    campaign = relationship("Campaign", back_populates="asset_groups")
    daily_metrics = relationship("AssetGroupDaily", back_populates="asset_group", cascade="all, delete-orphan")
    assets = relationship("AssetGroupAsset", back_populates="asset_group", cascade="all, delete-orphan")
    signals = relationship("AssetGroupSignal", back_populates="asset_group", cascade="all, delete-orphan")
