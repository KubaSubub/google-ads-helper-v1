"""Assets linked to PMax asset groups."""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class AssetGroupAsset(Base):
    __tablename__ = "asset_group_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_group_id = Column(Integer, ForeignKey("asset_groups.id", ondelete="CASCADE"), nullable=False)
    google_asset_id = Column(String(50), nullable=False)
    asset_type = Column(String(30), nullable=False)
    field_type = Column(String(50), nullable=True)
    text_content = Column(String(2000), nullable=True)
    performance_label = Column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("asset_group_id", "google_asset_id", "field_type", name="uq_asset_group_asset"),
        Index("idx_asset_group_asset_type", "asset_type"),
    )

    asset_group = relationship("AssetGroup", back_populates="assets")
