"""Google Recommendation model — native Google Ads recommendations."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class GoogleRecommendation(Base):
    __tablename__ = "google_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)

    google_recommendation_id = Column(String(200), nullable=False)
    recommendation_type = Column(String(100), nullable=False)  # KEYWORD, SITELINK_EXTENSION, etc.
    impact_estimate = Column(JSON, nullable=True)  # {base_metrics, potential_metrics}

    description = Column(String(2000), nullable=True)
    campaign_name = Column(String(500), nullable=True)

    status = Column(String(20), default="ACTIVE")  # ACTIVE, DISMISSED, APPLIED
    dismissed = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        UniqueConstraint("client_id", "google_recommendation_id", name="uq_google_recommendation"),
    )

    client = relationship("Client")
    campaign = relationship("Campaign")
