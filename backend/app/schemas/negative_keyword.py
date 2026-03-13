"""Negative keyword response schema."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NegativeKeywordResponse(BaseModel):
    id: int
    client_id: int
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    ad_group_id: Optional[int] = None
    ad_group_name: Optional[str] = None
    google_criterion_id: Optional[str] = None
    google_resource_name: Optional[str] = None
    criterion_kind: str = "NEGATIVE"
    negative_scope: str
    status: str
    source: str
    text: str
    match_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
