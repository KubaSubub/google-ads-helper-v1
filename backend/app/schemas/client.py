"""Client schemas."""

from datetime import datetime
from pydantic import BaseModel
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


class ClientResponse(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
