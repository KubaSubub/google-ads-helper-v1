"""Client model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    google_customer_id = Column(String(20), unique=True, nullable=False)
    industry = Column(String(100))
    website = Column(String(500))
    target_audience = Column(Text)
    usp = Column(Text)  # Unique Selling Proposition
    competitors = Column(JSON, default=list)  # ["competitor1.pl", ...]
    seasonality = Column(JSON, default=list)  # [{period, multiplier}, ...]
    business_rules = Column(JSON, default=dict)  # {min_roas, max_daily_budget, ...}
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(timezone.utc))
    last_change_sync_at = Column(DateTime, nullable=True)  # Last successful change_event sync

    # Relationships
    campaigns = relationship("Campaign", back_populates="client", cascade="all, delete-orphan")
