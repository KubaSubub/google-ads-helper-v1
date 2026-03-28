"""Auction Insight model — competitor visibility metrics per campaign."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AuctionInsight(Base):
    __tablename__ = "auction_insights"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    display_domain = Column(String(500), nullable=False)

    # All metrics are ratios 0.0–1.0
    impression_share = Column(Float, default=0.0)
    overlap_rate = Column(Float, default=0.0)
    position_above_rate = Column(Float, default=0.0)
    outranking_share = Column(Float, default=0.0)
    top_of_page_rate = Column(Float, default=0.0)
    abs_top_of_page_rate = Column(Float, default=0.0)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    campaign = relationship("Campaign")

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", "display_domain", name="uq_auction_insight_campaign_date_domain"),
    )
