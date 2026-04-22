"""Analytics package — domain-split of analytics_service.

Currently exposes AnalyticsBase; domain mixins land here in Faza 3.
"""

from app.services.analytics._shared import AnalyticsBase

__all__ = ["AnalyticsBase"]
