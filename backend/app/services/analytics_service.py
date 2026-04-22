"""Analytics service facade — assembled from domain mixins.

Backward-compatible entry point: `from app.services.analytics_service import AnalyticsService`
continues to work. Implementation lives in ``app.services.analytics`` (kpi,
health, breakdown, quality, pacing, bidding, waste, insights, pmax, comparison,
dsa) with shared helpers on ``AnalyticsBase``.
"""

from app.services.analytics._shared import AnalyticsBase
from app.services.analytics.bidding import BiddingMixin
from app.services.analytics.breakdown import BreakdownMixin
from app.services.analytics.comparison import ComparisonMixin
from app.services.analytics.dsa import DSAMixin
from app.services.analytics.health import HealthMixin
from app.services.analytics.insights import InsightsMixin
from app.services.analytics.kpi import KPIMixin
from app.services.analytics.pacing import PacingMixin
from app.services.analytics.pmax import PMaxMixin
from app.services.analytics.quality import QualityMixin
from app.services.analytics.waste import WasteMixin


class AnalyticsService(
    KPIMixin,
    HealthMixin,
    BreakdownMixin,
    QualityMixin,
    PacingMixin,
    BiddingMixin,
    WasteMixin,
    InsightsMixin,
    PMaxMixin,
    ComparisonMixin,
    DSAMixin,
    AnalyticsBase,
):
    """KPI aggregation, anomaly detection and domain analytics."""
