"""SyncCoverage model — tracks per-resource-type sync date ranges per client."""

from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class SyncCoverage(Base):
    __tablename__ = "sync_coverage"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(50), nullable=False)

    # Date range of synced data (NULL for structural/snapshot resources)
    data_from = Column(Date, nullable=True)
    data_to = Column(Date, nullable=True)

    last_sync_at = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
    last_status = Column(String(20), default="ok")  # ok | error

    __table_args__ = (
        UniqueConstraint("client_id", "resource_type", name="uq_sync_coverage_client_resource"),
    )

    client = relationship("Client")
