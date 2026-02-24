"""ActionLog model - tracks all actions executed on Google Ads API."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    action_type = Column(String, nullable=False)       # PAUSE_KEYWORD, UPDATE_BID, ADD_NEGATIVE, etc.
    entity_type = Column(String, nullable=False)        # keyword, ad, campaign, search_term
    entity_id = Column(String, nullable=False)          # Google Ads entity ID
    old_value_json = Column(Text, nullable=True)        # JSON: {"bid_micros": 1500000, "status": "ENABLED"}
    new_value_json = Column(Text, nullable=True)        # JSON: {"bid_micros": 2000000}
    status = Column(String, default="SUCCESS")          # SUCCESS, FAILED, REVERTED
    error_message = Column(Text, nullable=True)
    reverted_at = Column(DateTime, nullable=True)       # When action was reverted
    executed_at = Column(DateTime, default=lambda: datetime.utcnow())

    # Relationships
    client = relationship("Client")
