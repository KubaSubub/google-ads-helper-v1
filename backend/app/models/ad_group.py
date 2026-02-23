"""AdGroup model."""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AdGroup(Base):
    __tablename__ = "ad_groups"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    google_ad_group_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    bid_micros = Column(BigInteger, default=0)  # Max CPC bid in micros
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("campaign_id", "google_ad_group_id", name="uq_ad_group_google_id"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="ad_groups")
    keywords = relationship("Keyword", back_populates="ad_group", cascade="all, delete-orphan")
    search_terms = relationship("SearchTerm", back_populates="ad_group", cascade="all, delete-orphan")
    ads = relationship("Ad", back_populates="ad_group", cascade="all, delete-orphan")
