"""SyncLog model — tracks every sync operation with per-phase results."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="running")  # running | success | partial | failed
    days = Column(Integer, default=30)

    # Per-phase results: {"phase_name": {"count": N, "status": "ok|error", "error": "..."}}
    phases = Column(JSON, default=dict)

    # Summary counts
    total_synced = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    # Error message for overall failure (e.g., API not connected)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client")
