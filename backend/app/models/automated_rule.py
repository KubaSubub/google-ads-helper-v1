"""AutomatedRule + AutomatedRuleLog models — Feature F3: Automated Rules Engine."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.database import Base


class AutomatedRule(Base):
    """
    Stores automated rule definitions created by the user.
    Feature F3: Automated Rules Engine.
    """
    __tablename__ = "automated_rules"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    entity_type = Column(String(50), nullable=False)  # "keyword", "campaign", "search_term"
    conditions = Column(JSON, nullable=False)  # [{"field": "cost_micros", "op": ">", "value": 50000000}]
    action_type = Column(String(50), nullable=False)  # "PAUSE", "ADD_NEGATIVE", "ALERT"
    action_params = Column(JSON, nullable=True)
    check_interval_hours = Column(Integer, default=24, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    matches_last_run = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client")
    logs = relationship("AutomatedRuleLog", back_populates="rule", cascade="all, delete-orphan")


class AutomatedRuleLog(Base):
    """
    Stores execution logs for automated rules.
    """
    __tablename__ = "automated_rule_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("automated_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    matches_found = Column(Integer, default=0)
    actions_taken = Column(Integer, default=0)
    dry_run = Column(Boolean, default=True, nullable=False)
    result = Column(JSON, nullable=True)

    # Relationships
    rule = relationship("AutomatedRule", back_populates="logs")
