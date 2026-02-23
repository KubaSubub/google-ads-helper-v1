"""Pydantic schemas for API request/response serialization."""

from .common import (
    Priority,
    ActionStatus,
    ActionType,
    Segment,
    RecommendationStatus,
    MessageResponse,
    PaginatedResponse,
)
from .client import ClientBase, ClientCreate, ClientUpdate, ClientResponse
from .campaign import CampaignResponse, MetricDailyResponse
from .keyword import KeywordResponse
from .ad import AdResponse
from .search_term import SearchTermResponse
from .recommendation import RecommendationResponse, RecommendationSummary
from .analytics import (
    PeriodComparisonRequest,
    PeriodComparisonResponse,
    CorrelationRequest,
)

__all__ = [
    # Common
    "Priority",
    "ActionStatus",
    "ActionType",
    "Segment",
    "RecommendationStatus",
    "MessageResponse",
    "PaginatedResponse",
    # Client
    "ClientBase",
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    # Campaign
    "CampaignResponse",
    "MetricDailyResponse",
    # Keyword
    "KeywordResponse",
    # Ad
    "AdResponse",
    # Search Term
    "SearchTermResponse",
    # Recommendation
    "RecommendationResponse",
    "RecommendationSummary",
    # Analytics
    "PeriodComparisonRequest",
    "PeriodComparisonResponse",
    "CorrelationRequest",
]
