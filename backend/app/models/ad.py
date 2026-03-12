"""Ad model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_ad_id = Column(String(50))
    ad_type = Column(String(50))  # RESPONSIVE_SEARCH_AD, etc.
    status = Column(String(20))
    approval_status = Column(String(30), nullable=True)  # APPROVED, APPROVED_LIMITED, DISAPPROVED, UNDER_REVIEW
    ad_strength = Column(String(20), nullable=True)  # EXCELLENT, GOOD, AVERAGE, POOR, UNRATED
    final_url = Column(String(2000))

    # RSA components stored as JSON arrays
    headlines = Column(JSON, default=list)  # [{"text": "...", "pinned_position": null}, ...]
    descriptions = Column(JSON, default=list)

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Integer, default=0)  # Stored as micros

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    ad_group = relationship("AdGroup", back_populates="ads")

    @property
    def headline_1(self):
        """First headline from RSA headlines JSON."""
        if self.headlines and len(self.headlines) > 0:
            h = self.headlines[0]
            return h.get("text", h) if isinstance(h, dict) else str(h)
        return None

    @property
    def headline_2(self):
        """Second headline from RSA headlines JSON."""
        if self.headlines and len(self.headlines) > 1:
            h = self.headlines[1]
            return h.get("text", h) if isinstance(h, dict) else str(h)
        return None

