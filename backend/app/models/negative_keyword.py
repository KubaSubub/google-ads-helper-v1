"""Canonical cache model for negative keyword criteria."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class NegativeKeyword(Base):
    __tablename__ = "negative_keywords"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    google_criterion_id = Column(String(50), nullable=True, index=True)
    google_resource_name = Column(String(255), nullable=True)
    criterion_kind = Column(String(20), nullable=False, default="NEGATIVE")
    text = Column(String(500), nullable=False)
    match_type = Column(String(20), default="PHRASE")
    negative_scope = Column(String(20), default="CAMPAIGN")
    status = Column(String(20), default="ENABLED")
    source = Column(String(30), default="LOCAL_ACTION")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    client = relationship("Client")
    campaign = relationship("Campaign")
    ad_group = relationship("AdGroup")
