"""Audience signals and search themes for PMax asset groups."""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class AssetGroupSignal(Base):
    __tablename__ = "asset_group_signals"

    id = Column(Integer, primary_key=True, index=True)
    asset_group_id = Column(Integer, ForeignKey("asset_groups.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String(30), nullable=False)
    search_theme_text = Column(String(500), nullable=True)
    audience_resource_name = Column(String(500), nullable=True)
    audience_name = Column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("asset_group_id", "signal_type", "search_theme_text", "audience_resource_name",
                         name="uq_asset_group_signal"),
        Index("idx_asset_group_signal_type", "signal_type"),
    )

    asset_group = relationship("AssetGroup", back_populates="signals")
