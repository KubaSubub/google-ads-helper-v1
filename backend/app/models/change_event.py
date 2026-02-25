"""ChangeEvent model — tracks ALL changes to Google Ads account from any source."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Google Ads identifiers
    resource_name = Column(String, nullable=False, unique=True)  # dedup key
    change_date_time = Column(DateTime, nullable=False, index=True)

    # Who / what made the change
    user_email = Column(String, nullable=True)
    client_type = Column(String, nullable=False)  # GOOGLE_ADS_WEB_CLIENT, GOOGLE_ADS_API, etc.

    # What changed
    change_resource_type = Column(String, nullable=False)  # CAMPAIGN, AD_GROUP, AD_GROUP_CRITERION, etc.
    change_resource_name = Column(String, nullable=True)  # resource path of changed entity
    resource_change_operation = Column(String, nullable=False)  # CREATE, UPDATE, REMOVE

    # Change details (JSON)
    changed_fields = Column(Text, nullable=True)  # JSON array of field paths
    old_resource_json = Column(Text, nullable=True)  # JSON serialized protobuf
    new_resource_json = Column(Text, nullable=True)  # JSON serialized protobuf

    # Optional link to Helper action_log
    action_log_id = Column(Integer, ForeignKey("action_log.id"), nullable=True)

    # Denormalized for display
    entity_id = Column(String, nullable=True)
    entity_name = Column(String, nullable=True)
    campaign_name = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client")
    action_log = relationship("ActionLog")

    __table_args__ = (
        Index("ix_change_events_client_datetime", "client_id", "change_date_time"),
        Index("ix_change_events_resource_type", "change_resource_type"),
    )
