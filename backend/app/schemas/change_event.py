"""Change event schemas for API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChangeEventResponse(BaseModel):
    """Single change event for API response."""
    id: int
    client_id: int
    resource_name: str
    change_date_time: datetime
    user_email: Optional[str] = None
    client_type: str
    change_resource_type: str
    change_resource_name: Optional[str] = None
    resource_change_operation: str
    changed_fields: Optional[str] = None
    old_resource_json: Optional[str] = None
    new_resource_json: Optional[str] = None
    action_log_id: Optional[int] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    campaign_name: Optional[str] = None
    is_helper_action: bool = False

    model_config = {"from_attributes": True}


class ChangeEventListResponse(BaseModel):
    """Paginated list of change events."""
    total: int
    limit: int
    offset: int
    events: list[ChangeEventResponse]


class UnifiedTimelineEntry(BaseModel):
    """Single entry in the unified timeline (action_log OR change_event)."""
    source: str  # "helper" or "external"
    timestamp: datetime
    operation: str  # action_type or resource_change_operation
    resource_type: str  # entity_type or change_resource_type
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    campaign_name: Optional[str] = None
    user_email: Optional[str] = None
    client_type: Optional[str] = None
    status: Optional[str] = None  # For helper actions: SUCCESS/FAILED/REVERTED
    old_value_json: Optional[str] = None
    new_value_json: Optional[str] = None
    changed_fields: Optional[str] = None
    action_log_id: Optional[int] = None
    change_event_id: Optional[int] = None
    can_revert: bool = False


class UnifiedTimelineResponse(BaseModel):
    """Paginated unified timeline."""
    total: int
    limit: int
    offset: int
    entries: list[UnifiedTimelineEntry]
