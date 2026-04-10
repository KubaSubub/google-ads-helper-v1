"""Client schemas."""

from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional


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
    currency: Optional[str] = "PLN"


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
    currency: Optional[str] = None

    @field_validator("business_rules")
    @classmethod
    def validate_business_rules(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return v
        numeric_gte0 = ("target_cpa", "target_roas", "ltv_per_customer", "min_roas", "max_daily_budget")
        for field in numeric_gte0:
            val = v.get(field)
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                raise ValueError(f"{field} must be a non-negative number")
        margin = v.get("profit_margin_pct")
        if margin is not None and (not isinstance(margin, (int, float)) or not (0 <= margin <= 100)):
            raise ValueError("profit_margin_pct must be between 0 and 100")
        brand_terms = v.get("brand_terms")
        if brand_terms is not None:
            if not isinstance(brand_terms, list):
                raise ValueError("brand_terms must be a list")
            if len(brand_terms) > 50:
                raise ValueError("brand_terms may not exceed 50 items")
            if any(not isinstance(t, str) or len(t) > 200 for t in brand_terms):
                raise ValueError("each brand term must be a string of at most 200 characters")
        priority_conversions = v.get("priority_conversions")
        if priority_conversions is not None:
            if not isinstance(priority_conversions, list):
                raise ValueError("priority_conversions must be a list")
            if len(priority_conversions) > 20:
                raise ValueError("priority_conversions may not exceed 20 items")
        return v


class ClientResponse(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Client Health ──────────────────────────────────────────────────────────────

class AccountMetadata(BaseModel):
    customer_id: str
    name: str
    account_type: str = "STANDARD"   # "MCC" | "STANDARD"
    currency: str = "PLN"
    timezone: Optional[str] = None
    auto_tagging_enabled: Optional[bool] = None
    tracking_url_template: Optional[str] = None


class SyncHealth(BaseModel):
    last_synced_at: Optional[datetime] = None
    hours_since_sync: Optional[float] = None
    freshness: str = "red"           # "green" | "yellow" | "red"
    last_status: Optional[str] = None
    last_duration_seconds: Optional[float] = None


class ConversionActionSummary(BaseModel):
    name: str
    category: Optional[str] = None
    status: str
    include_in_conversions: bool = False


class ConversionTracking(BaseModel):
    active_count: int = 0
    attribution_model: Optional[str] = None
    enhanced_conversions_enabled: Optional[bool] = None  # not available from DB
    actions: list[ConversionActionSummary] = []


class LinkedAccount(BaseModel):
    type: str       # "GA4" | "MERCHANT_CENTER" | "YOUTUBE" | "SEARCH_CONSOLE"
    status: str     # "linked" | "not_linked"
    resource_name: Optional[str] = None
    detected_via: str = "google_ads_api"


class ClientHealthResponse(BaseModel):
    account_metadata: AccountMetadata
    sync_health: SyncHealth
    conversion_tracking: ConversionTracking
    linked_accounts: list[LinkedAccount] = []
    errors: list[str] = []
