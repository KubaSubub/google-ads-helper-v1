"""Bid Modifier model — device, location, and schedule bid adjustments."""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class BidModifier(Base):
    __tablename__ = "bid_modifiers"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=True)
    google_criterion_id = Column(String(50), nullable=True)

    # Modifier type
    modifier_type = Column(String(30), nullable=False)  # DEVICE, LOCATION, AD_SCHEDULE, AUDIENCE
    # Type-specific value
    device_type = Column(String(20), nullable=True)      # MOBILE, DESKTOP, TABLET
    location_id = Column(String(50), nullable=True)       # Geo target constant ID
    location_name = Column(String(200), nullable=True)    # Resolved location name
    # Ad schedule fields
    day_of_week = Column(String(15), nullable=True)       # MONDAY, TUESDAY, etc.
    start_hour = Column(Integer, nullable=True)           # 0-23
    end_hour = Column(Integer, nullable=True)             # 0-24
    start_minute = Column(String(10), nullable=True)      # ZERO, FIFTEEN, THIRTY, FORTY_FIVE
    end_minute = Column(String(10), nullable=True)

    # The actual bid modifier (1.0 = no change, 1.2 = +20%, 0.8 = -20%, 0 = exclude)
    bid_modifier = Column(Float, default=1.0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "modifier_type", "device_type", "location_id",
                         "day_of_week", "start_hour", name="uq_bid_modifier"),
        Index("idx_bid_modifier_type", "modifier_type"),
    )

    campaign = relationship("Campaign")
    ad_group = relationship("AdGroup")
