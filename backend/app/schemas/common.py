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


class ActionStatus(str, Enum):
    """Action log status."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERTED = "REVERTED"


class ActionType(str, Enum):
    """Types of actions that can be executed on Google Ads."""
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    ENABLE_KEYWORD = "ENABLE_KEYWORD"
    UPDATE_BID = "UPDATE_BID"
    ADD_KEYWORD = "ADD_KEYWORD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    PAUSE_AD = "PAUSE_AD"
    INCREASE_BUDGET = "INCREASE_BUDGET"
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
