"""ScheduledSyncConfig model — stores per-client sync schedule configuration."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ScheduledSyncConfig(Base):
    """
    Stores scheduled sync configuration per client.
    Feature F1: Scheduled Sync & Alerts.
    """
    __tablename__ = "scheduled_sync_configs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    enabled = Column(Boolean, default=False, nullable=False)
    interval_hours = Column(Integer, default=6, nullable=False)  # sync every N hours
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client")
