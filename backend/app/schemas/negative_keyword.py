"""Negative keyword schemas."""

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


class NegativeKeywordCreate(BaseModel):
    client_id: int
    campaign_id: Optional[int] = None
    ad_group_id: Optional[int] = None
    texts: list[str]
    match_type: str = "PHRASE"
    negative_scope: str = "CAMPAIGN"


class NegativeKeywordListResponse(BaseModel):
    id: int
    client_id: int
    name: str
    description: Optional[str] = None
    item_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NegativeKeywordListItemResponse(BaseModel):
    id: int
    text: str
    match_type: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NegativeKeywordListDetailResponse(NegativeKeywordListResponse):
    items: list[NegativeKeywordListItemResponse] = []


class NegativeKeywordListCreate(BaseModel):
    client_id: int
    name: str
    description: Optional[str] = None


class NegativeKeywordListAddItems(BaseModel):
    texts: list[str]
    match_type: str = "PHRASE"


class ApplyListRequest(BaseModel):
    campaign_ids: list[int] = []
    ad_group_ids: list[int] = []
