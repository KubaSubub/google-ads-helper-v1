"""Daily metrics for PMax asset groups."""

from sqlalchemy import Column, Integer, Float, BigInteger, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class AssetGroupDaily(Base):
    __tablename__ = "asset_group_daily"

    id = Column(Integer, primary_key=True, index=True)
    asset_group_id = Column(Integer, ForeignKey("asset_groups.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    cost_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("asset_group_id", "date", name="uq_asset_group_daily"),
        Index("idx_asset_group_daily_date", "date"),
    )

    asset_group = relationship("AssetGroup", back_populates="daily_metrics")
