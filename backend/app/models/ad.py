"""Ad model."""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_ad_id = Column(String(50))
    ad_type = Column(String(50))  # RESPONSIVE_SEARCH_AD, etc.
    status = Column(String(20))
    final_url = Column(String(2000))

    # RSA components stored as JSON arrays
    headlines = Column(JSON, default=list)  # [{"text": "...", "pinned_position": null}, ...]
    descriptions = Column(JSON, default=list)

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Integer, default=0)
    ctr = Column(Integer, default=0)  # Stored as micros

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
