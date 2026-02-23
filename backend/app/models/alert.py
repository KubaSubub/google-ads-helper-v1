"""Alert model - anomaly detection alerts (Feature 7)."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    """
    Stores anomaly detection alerts.
    Feature 7: Spend spikes, conversion drops, CTR drops.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)         # SPEND_SPIKE, CONVERSION_DROP, CTR_DROP
    severity = Column(String, default="MEDIUM")         # HIGH, MEDIUM
    title = Column(String, nullable=False)
    description = Column(Text)
    metric_value = Column(String, nullable=True)        # "Spend: $500 (avg: $200)"
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    client = relationship("Client")
    campaign = relationship("Campaign")
