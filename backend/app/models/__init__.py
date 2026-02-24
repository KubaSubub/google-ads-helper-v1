"""ORM models for Google Ads Helper.

Import all models here for easy access.
"""

from .client import Client
from .campaign import Campaign
from .ad_group import AdGroup
from .keyword import Keyword
from .search_term import SearchTerm
from .ad import Ad
from .metric_daily import MetricDaily
from .metric_segmented import MetricSegmented
from .recommendation import Recommendation
from .action_log import ActionLog
from .alert import Alert

__all__ = [
    "Client",
    "Campaign",
    "AdGroup",
    "Keyword",
    "SearchTerm",
    "Ad",
    "MetricDaily",
    "MetricSegmented",
    "Recommendation",
    "ActionLog",
    "Alert",
]
