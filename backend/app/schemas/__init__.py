"""Pydantic schemas for API request/response serialization."""

from .common import (
    ActionStatus,
    ActionType,
    CampaignRole,
    ContextOutcome,
    MessageResponse,
    PaginatedResponse,
    Priority,
    ProtectionLevel,
    RecommendationStatus,
    RoleSource,
    Segment,
)
from .client import ClientBase, ClientCreate, ClientResponse, ClientUpdate
from .campaign import CampaignResponse, CampaignUpdate, MetricDailyResponse
from .keyword import KeywordResponse
from .negative_keyword import NegativeKeywordResponse
from .ad import AdResponse
from .search_term import SearchTermResponse
from .recommendation import RecommendationResponse, RecommendationSummary
from .analytics import CorrelationRequest, PeriodComparisonRequest, PeriodComparisonResponse

__all__ = [
    "Priority",
    "ActionStatus",
    "ActionType",
    "Segment",
    "RecommendationStatus",
    "CampaignRole",
    "ProtectionLevel",
    "RoleSource",
    "ContextOutcome",
    "MessageResponse",
    "PaginatedResponse",
    "ClientBase",
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "CampaignResponse",
    "CampaignUpdate",
    "MetricDailyResponse",
    "KeywordResponse",
    "NegativeKeywordResponse",
    "AdResponse",
    "SearchTermResponse",
    "RecommendationResponse",
    "RecommendationSummary",
    "PeriodComparisonRequest",
    "PeriodComparisonResponse",
    "CorrelationRequest",
]
