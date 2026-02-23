"""Keyword schema."""

from datetime import datetime
from pydantic import BaseModel, computed_field, Field
from typing import Optional


class KeywordResponse(BaseModel):
    id: int
    ad_group_id: int
    google_keyword_id: Optional[str] = None
    text: str
    match_type: Optional[str] = None
    status: Optional[str] = None
    final_url: Optional[str] = None
    bid_micros: int = 0
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0
    ctr_micros: int = Field(0, alias="ctr")
    avg_cpc_micros: int = 0
    cpa_micros: int = 0
    quality_score: int = 0
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
        return round(self.ctr_micros / 100_00, 2)

    model_config = {"from_attributes": True, "populate_by_name": True}
