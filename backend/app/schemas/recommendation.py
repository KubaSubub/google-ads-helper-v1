"""Recommendation schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from .common import Priority, RecommendationStatus


class RecommendationResponse(BaseModel):
    """Recommendation response schema."""
    id: int
    client_id: int
    rule_id: str
    entity_type: str
    entity_id: str
    priority: Priority
    reason: str
    suggested_action: str  # JSON string
    status: RecommendationStatus
    created_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecommendationSummary(BaseModel):
    """Summary of recommendations grouped by priority/status."""
    total: int
    pending: int
    applied: int
    dismissed: int
    high_priority: int
    medium_priority: int
    low_priority: int
