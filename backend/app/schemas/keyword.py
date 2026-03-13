"""Keyword schema."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class KeywordResponse(BaseModel):
    id: int
    ad_group_id: int
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    ad_group_name: Optional[str] = None
    google_keyword_id: Optional[str] = None
    criterion_kind: str = "POSITIVE"
    text: str
    match_type: Optional[str] = None
    status: Optional[str] = None
    serving_status: Optional[str] = None
    final_url: Optional[str] = None
    bid_micros: int = 0
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    conversion_value_micros: int = 0
    ctr_micros: int = Field(0, alias="ctr")
    avg_cpc_micros: int = 0
    cpa_micros: int = 0
    quality_score: int = 0

    # Impression share (keyword-level, rank-based only)
    search_impression_share: Optional[float] = None
    search_top_impression_share: Optional[float] = None
    search_abs_top_impression_share: Optional[float] = None
    search_rank_lost_is: Optional[float] = None
    search_rank_lost_top_is: Optional[float] = None
    search_rank_lost_abs_top_is: Optional[float] = None
    search_exact_match_is: Optional[float] = None

    # Historical QS components (1=below avg, 2=avg, 3=above avg)
    historical_quality_score: Optional[int] = None
    historical_creative_quality: Optional[int] = None
    historical_landing_page_quality: Optional[int] = None
    historical_search_predicted_ctr: Optional[int] = None

    # Extended conversions
    all_conversions: Optional[float] = None
    all_conversions_value_micros: Optional[int] = None
    cross_device_conversions: Optional[float] = None
    value_per_conversion_micros: Optional[int] = None
    conversions_value_per_cost: Optional[float] = None

    # Top impression %
    abs_top_impression_pct: Optional[float] = None
    top_impression_pct: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def bid(self) -> float:
        return round(self.bid_micros / 1_000_000, 2)

    @computed_field
    @property
    def cost(self) -> float:
        return round(self.cost_micros / 1_000_000, 2)

    @computed_field
    @property
    def avg_cpc(self) -> float:
        return round(self.avg_cpc_micros / 1_000_000, 2)

    @computed_field
    @property
    def cpa(self) -> float:
        return round(self.cpa_micros / 1_000_000, 2)

    @computed_field
    @property
    def ctr(self) -> float:
        return round(self.ctr_micros / 10_000, 2)

    @computed_field
    @property
    def conversion_value(self) -> float:
        return round(self.conversion_value_micros / 1_000_000, 2)

    @computed_field
    @property
    def roas(self) -> float:
        cost = self.cost_micros / 1_000_000
        cv = self.conversion_value_micros / 1_000_000
        return round(cv / cost, 2) if cost > 0 else 0.0

    model_config = {"from_attributes": True, "populate_by_name": True}
