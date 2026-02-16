"""Pydantic schemas for API request/response serialization."""

from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ClientBase(BaseModel):
    name: str
    google_customer_id: str
    industry: Optional[str] = None
    website: Optional[str] = None
    target_audience: Optional[str] = None
    usp: Optional[str] = None
    competitors: list[str] = []
    seasonality: list[dict] = []
    business_rules: dict = {}
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    target_audience: Optional[str] = None
    usp: Optional[str] = None
    competitors: Optional[list[str]] = None
    seasonality: Optional[list[dict]] = None
    business_rules: Optional[dict] = None
    notes: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

class CampaignResponse(BaseModel):
    id: int
    client_id: int
    google_campaign_id: str
    name: str
    status: Optional[str] = None
    campaign_type: Optional[str] = None
    budget_amount: Optional[float] = None
    budget_type: Optional[str] = None
    bidding_strategy: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Search Term
# ---------------------------------------------------------------------------

class SearchTermResponse(BaseModel):
    id: int
    ad_group_id: int
    text: str
    keyword_text: Optional[str] = None
    match_type: Optional[str] = None
    clicks: int = 0
    impressions: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0
    date_from: date
    date_to: date

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Keyword
# ---------------------------------------------------------------------------

class KeywordResponse(BaseModel):
    id: int
    ad_group_id: int
    text: str
    match_type: Optional[str] = None
    status: Optional[str] = None
    final_url: Optional[str] = None
    cpc_bid: Optional[float] = None
    clicks: int = 0
    impressions: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Ad
# ---------------------------------------------------------------------------

class AdResponse(BaseModel):
    id: int
    ad_group_id: int
    google_ad_id: Optional[str] = None
    ad_type: Optional[str] = None
    status: Optional[str] = None
    final_url: Optional[str] = None
    headlines: list[dict] = []
    descriptions: list[dict] = []
    clicks: int = 0
    impressions: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricDailyResponse(BaseModel):
    id: int
    campaign_id: int
    date: date
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    conversions: float = 0.0
    conversion_rate: float = 0.0
    cost: float = 0.0
    cost_per_conversion: float = 0.0
    roas: float = 0.0
    avg_cpc: float = 0.0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class PeriodComparisonRequest(BaseModel):
    campaign_id: int
    metric: str
    period_a_start: date
    period_a_end: date
    period_b_start: date
    period_b_end: date


class PeriodComparisonResponse(BaseModel):
    metric: str
    period_a_mean: float
    period_b_mean: float
    change_pct: float
    trend: str  # "up" | "down" | "stable"
    is_significant: bool
    p_value: float


class CorrelationRequest(BaseModel):
    campaign_ids: list[int] = []
    metrics: list[str] = Field(
        default=["clicks", "impressions", "ctr", "conversions", "cost", "roas"]
    )
    date_from: Optional[date] = None
    date_to: Optional[date] = None


# ---------------------------------------------------------------------------
# Automated Rules
# ---------------------------------------------------------------------------

class RuleCreate(BaseModel):
    client_id: int
    name: str
    description: Optional[str] = None
    conditions: dict  # {all: [{metric, operator, value}, ...]}
    actions: list[dict]  # [{type, params}, ...]
    entity_type: str = "keyword"
    frequency: str = "weekly"
    require_approval: bool = True


class RuleResponse(BaseModel):
    id: int
    client_id: int
    name: str
    description: Optional[str] = None
    conditions: dict
    actions: list[dict]
    entity_type: str
    frequency: str
    require_approval: bool
    is_active: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutionQueueItemResponse(BaseModel):
    id: int
    rule_id: int
    action_type: str
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[str] = None
    params: dict = {}
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True
