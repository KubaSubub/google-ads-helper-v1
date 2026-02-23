"""Search term schemas with micros→USD conversion."""

from datetime import date
from pydantic import BaseModel, computed_field
from typing import Optional


class SearchTermResponse(BaseModel):
    """Search term response with micros→USD conversion."""
    id: int
    ad_group_id: int
    text: str
    keyword_text: Optional[str] = None
    match_type: Optional[str] = None
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0
    ctr: int = 0  # Stored as micros
    conversion_rate: int = 0  # Stored as micros
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
        """Convert CTR from micros to percentage."""
        return round(self.ctr / 10_000, 2)

    @computed_field
    @property
    def conversion_rate_pct(self) -> float:
        """Convert conversion rate from micros to percentage."""
        return round(self.conversion_rate / 10_000, 2)

    @computed_field
    @property
    def cost_per_conversion_usd(self) -> float:
        """Calculated: cost / conversions."""
        if self.conversions > 0:
            return round(self.cost_micros / self.conversions / 1_000_000, 2)
        return 0.0

    model_config = {"from_attributes": True}
