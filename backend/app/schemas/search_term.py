"""Search term schemas with micros→USD conversion."""

from datetime import date
from pydantic import BaseModel, computed_field
from typing import Optional


class SearchTermResponse(BaseModel):
    """Search term response with micros→USD conversion."""
    id: int
    ad_group_id: Optional[int] = None
    campaign_id: Optional[int] = None
    text: str
    keyword_text: Optional[str] = None
    match_type: Optional[str] = None
    segment: Optional[str] = None
    source: Optional[str] = "SEARCH"
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    conversion_value_micros: int = 0
    ctr: float = 0.0  # Percentage (5.0 = 5%)
    conversion_rate: float = 0.0  # Percentage (5.0 = 5%)
    date_from: date
    date_to: date

    @computed_field
    @property
    def cost_usd(self) -> float:
        """Convert cost from micros to USD."""
        return round(self.cost_micros / 1_000_000, 2)

    @computed_field
    @property
    def ctr_pct(self) -> float:
        """CTR as percentage (backward compat alias)."""
        return round(self.ctr, 2)

    @computed_field
    @property
    def conversion_rate_pct(self) -> float:
        """Conversion rate as percentage (backward compat alias)."""
        return round(self.conversion_rate, 2)

    @computed_field
    @property
    def cost_per_conversion_usd(self) -> float:
        """Calculated: cost / conversions."""
        if self.conversions > 0:
            return round(self.cost_micros / self.conversions / 1_000_000, 2)
        return 0.0

    @computed_field
    @property
    def conversion_value_usd(self) -> float:
        """Revenue in USD."""
        return round(self.conversion_value_micros / 1_000_000, 2)

    @computed_field
    @property
    def roas(self) -> float:
        """Real ROAS = revenue / cost."""
        cost = self.cost_micros / 1_000_000
        cv = self.conversion_value_micros / 1_000_000
        return round(cv / cost, 2) if cost > 0 else 0.0

    model_config = {"from_attributes": True}
