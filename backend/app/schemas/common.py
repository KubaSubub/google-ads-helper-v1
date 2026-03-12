"""Common enums and base schemas."""

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Priority(str, Enum):
    """Recommendation priority levels."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationSource(str, Enum):
    """Sources feeding the unified recommendation stream."""

    PLAYBOOK_RULES = "PLAYBOOK_RULES"
    GOOGLE_ADS_API = "GOOGLE_ADS_API"
    HYBRID = "HYBRID"
    ANALYTICS = "ANALYTICS"


class ActionStatus(str, Enum):
    """Action log status."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    DRY_RUN = "DRY_RUN"
    REVERTED = "REVERTED"


class ActionType(str, Enum):
    """Types of actions that can be executed on Google Ads."""

    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    ENABLE_KEYWORD = "ENABLE_KEYWORD"
    UPDATE_BID = "UPDATE_BID"
    SET_KEYWORD_BID = "SET_KEYWORD_BID"
    ADD_KEYWORD = "ADD_KEYWORD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    PAUSE_AD = "PAUSE_AD"
    INCREASE_BUDGET = "INCREASE_BUDGET"
    SET_BUDGET = "SET_BUDGET"
    DECREASE_BUDGET = "DECREASE_BUDGET"


class Segment(str, Enum):
    """Search term segmentation categories."""

    IRRELEVANT = "IRRELEVANT"
    HIGH_PERFORMER = "HIGH_PERFORMER"
    WASTE = "WASTE"
    OTHER = "OTHER"


class RecommendationStatus(str, Enum):
    """Recommendation status."""

    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class CampaignRole(str, Enum):
    BRAND = "BRAND"
    GENERIC = "GENERIC"
    PROSPECTING = "PROSPECTING"
    REMARKETING = "REMARKETING"
    PMAX = "PMAX"
    LOCAL = "LOCAL"
    UNKNOWN = "UNKNOWN"


class ProtectionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RoleSource(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class ContextOutcome(str, Enum):
    ACTION = "ACTION"
    INSIGHT_ONLY = "INSIGHT_ONLY"
    BLOCKED_BY_CONTEXT = "BLOCKED_BY_CONTEXT"


class MessageResponse(BaseModel):
    """Generic success/error message response."""

    message: str
    success: bool = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated list responses."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
