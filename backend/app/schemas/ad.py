"""Ad schema."""

from datetime import datetime
from pydantic import BaseModel, computed_field
from typing import Optional, Any


class AdResponse(BaseModel):
    id: int
    ad_group_id: int
    google_ad_id: Optional[str] = None
    ad_type: Optional[str] = None
    status: Optional[str] = None
    final_url: Optional[str] = None
    headlines: Any = []
    descriptions: Any = []
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0
    ctr: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def cost(self) -> float:
        return round(self.cost_micros / 1_000_000, 2)

    model_config = {"from_attributes": True}
