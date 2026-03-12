"""NegativeKeyword shadow model for campaign-level negatives."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class NegativeKeyword(Base):
    __tablename__ = "negative_keywords"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    text = Column(String(500), nullable=False)
    match_type = Column(String(20), default="PHRASE")
    level = Column(String(20), default="CAMPAIGN")
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    client = relationship("Client")
    campaign = relationship("Campaign")


