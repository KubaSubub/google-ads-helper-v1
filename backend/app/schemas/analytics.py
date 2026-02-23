"""Analytics-related request/response schemas."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


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
        default=["clicks", "impressions", "ctr", "conversions", "cost_micros", "roas"]
    )
    date_from: Optional[date] = None
    date_to: Optional[date] = None
