"""Campaign & MetricDaily schemas with micros→currency conversion."""

from datetime import date, datetime
from pydantic import BaseModel, computed_field
from typing import Optional


class MetricDailyResponse(BaseModel):
    """Daily metrics for a campaign."""
    id: int
    campaign_id: int
    date: date
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    conversions: float = 0
    conversion_rate: float = 0.0
    cost_micros: int = 0
    roas: float = 0.0
    avg_cpc_micros: int = 0

    @computed_field
    @property
    def cost(self) -> float:
        return round(self.cost_micros / 1_000_000, 2)

    @computed_field
    @property
    def avg_cpc(self) -> float:
        return round(self.avg_cpc_micros / 1_000_000, 2)

    model_config = {"from_attributes": True}


class CampaignResponse(BaseModel):
    """Campaign response with micros→USD conversion via @computed_field."""
    id: int
    client_id: int
    google_campaign_id: str
    name: str
    status: Optional[str] = None
    campaign_type: Optional[str] = None
    budget_micros: int = 0
    budget_type: Optional[str] = None
    bidding_strategy: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def budget_usd(self) -> float:
        """Convert budget from micros to USD for display."""
        return round(self.budget_micros / 1_000_000, 2)

    model_config = {"from_attributes": True}
