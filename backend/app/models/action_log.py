"""ActionLog model - tracks all actions executed on Google Ads API."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ActionLog(Base):
    """
    Logs every action executed on Google Ads API.
    Enables undo/revert functionality (Feature 4).

    CRITICAL: old_value_json MUST be saved BEFORE executing action.
    """
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    action_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    status = Column(String, default="SUCCESS")
    error_message = Column(Text, nullable=True)
    execution_mode = Column(String, default="LIVE")
    precondition_status = Column(String, nullable=True)
    context_json = Column(JSON, nullable=True)
    action_payload = Column(JSON, nullable=True)
    reverted_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    client = relationship("Client")


