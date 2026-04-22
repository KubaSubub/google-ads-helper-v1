"""Analytics endpoints — KPIs, anomaly detection, correlation, forecasting."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime, timezone

try:
    import numpy as np
    import pandas as pd
    from scipy.stats import ttest_ind
except ImportError as _import_err:
    raise ImportError(
        "Analytics router requires numpy, pandas, and scipy. "
        "Install them with: pip install numpy pandas scipy"
    ) from _import_err

from app.demo_guard import ensure_demo_write_allowed
from app.database import get_db
from app.dependencies import CommonFilters, common_filters
from app.models import MetricDaily, Campaign, Client, Keyword, KeywordDaily, AdGroup, Alert, MetricSegmented
from app.schemas import PeriodComparisonRequest, PeriodComparisonResponse, CorrelationRequest
from app.services.analytics_service import AnalyticsService
from app.services.cache import dashboard_kpis_cache
from app.utils.formatters import micros_to_currency
from app.utils.date_utils import resolve_dates

router = APIRouter()

# Unified metric names shared across /trends, /correlation, /wow-comparison.
# Frontend TrendExplorer uses these exact keys.
TREND_METRICS = {
    "cost", "clicks", "impressions", "conversions", "conversion_value",
    "ctr", "cpc", "cpa", "cvr", "roas",
    "search_impression_share", "search_top_impression_share", "search_abs_top_impression_share",
    "search_budget_lost_is", "search_rank_lost_is", "search_click_share",
    "abs_top_impression_pct", "top_impression_pct",
}
# Backward-compat aliases accepted by /correlation for clients sending legacy names.
CORRELATION_LEGACY_ALIASES = {
    "cost_micros": "cost",
    "avg_cpc_micros": "cpc",
    "conversion_rate": "cvr",
}
# Raw MetricDaily column names used by /compare-periods and /forecast (getattr-based).
# These are actual SQLAlchemy columns — do not mix with TREND_METRICS.
LEGACY_COLUMN_METRICS = {
    "clicks", "impressions", "ctr", "conversions", "conversion_rate",
    "cost_micros", "roas", "avg_cpc_micros",
}
VALID_METRICS = TREND_METRICS  # /correlation uses this set
FORECAST_METRIC_ALIASES = {
    "cost": "cost_micros",
    "cpc": "avg_cpc_micros",
}
FORECAST_MICROS_METRICS = {"cost_micros", "avg_cpc_micros"}


# ---------------------------------------------------------------------------
# KPIs & Anomaly Detection — delegated to AnalyticsService
# ---------------------------------------------------------------------------


# /kpis moved to routers/analytics/_kpis.py


# Anomaly endpoints (/anomalies, /anomalies/{id}/resolve, /detect, /z-score-anomalies)
# moved to routers/analytics/_health.py


# ---------------------------------------------------------------------------
# Advanced Analytics (correlation, period comparison, forecast)
# ---------------------------------------------------------------------------


# /correlation + /compare-periods moved to routers/analytics/_insights.py


# /dashboard-kpis moved to routers/analytics/_kpis.py


# /quality-score-audit moved to routers/analytics/_quality.py


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


# /forecast moved to routers/analytics/_insights.py


# ---------------------------------------------------------------------------
# NEW V2 Endpoints — TrendExplorer, Health Score, Campaign Trends
# ---------------------------------------------------------------------------


# /trends moved to routers/analytics/_kpis.py


# /trends-by-device moved to routers/analytics/_breakdown.py


# /health-score moved to routers/analytics/_health.py


# /campaign-trends + /wow-comparison moved to routers/analytics/_kpis.py


# ---------------------------------------------------------------------------
# Campaigns Summary — per-campaign aggregated metrics for dashboard table
# ---------------------------------------------------------------------------


# /campaigns-summary moved to routers/analytics/_kpis.py


# ---------------------------------------------------------------------------
# Budget Pacing — underspend / overspend tracking
# ---------------------------------------------------------------------------


# /budget-pacing moved to routers/analytics/_pacing.py


# ---------------------------------------------------------------------------
# Impression Share Trends
# ---------------------------------------------------------------------------


# /impression-share, /device-breakdown, /geo-breakdown moved to routers/analytics/_breakdown.py


# ---------------------------------------------------------------------------
# Dayparting — day-of-week performance
# ---------------------------------------------------------------------------


# /dayparting moved to routers/analytics/_pacing.py


# ---------------------------------------------------------------------------
# RSA Analysis — ad copy performance
# ---------------------------------------------------------------------------


# /rsa-analysis, /ngram-analysis, /match-type-analysis, /landing-pages,
# /landing-page-diagnostics moved to routers/analytics/_quality.py


# ---------------------------------------------------------------------------
# Dayparting — hourly breakdown + bid-schedule suggestions
# ---------------------------------------------------------------------------


# dayparting-hourly-suggestions, -dow-suggestions, -heatmap moved to _pacing.py


# ---------------------------------------------------------------------------
# Shopping product-group performance + feed heuristics
# ---------------------------------------------------------------------------


# /shopping-product-groups (severity audit) moved to routers/analytics/_shopping.py


# ---------------------------------------------------------------------------
# Offline conversion import lag tracker
# ---------------------------------------------------------------------------


# /offline-conversion-lag + /seasonal-comparison moved to _pacing.py


# ---------------------------------------------------------------------------
# Audience overlap / redundancy
# ---------------------------------------------------------------------------


# /audience-overlap moved to routers/analytics/_audience.py


# ---------------------------------------------------------------------------
# Wasted Spend — zero-conversion waste summary
# ---------------------------------------------------------------------------


# /wasted-spend, /account-structure moved to routers/analytics/_waste.py


# ---------------------------------------------------------------------------
# Bidding Strategy Advisor — recommend optimal strategy per campaign
# ---------------------------------------------------------------------------


# /bidding-advisor moved to routers/analytics/_bidding.py


# ---------------------------------------------------------------------------
# Hourly Dayparting — performance by hour of day
# ---------------------------------------------------------------------------


# /hourly-dayparting moved to _pacing.py


# ---------------------------------------------------------------------------
# B2: Search Terms Trend Analysis
# ---------------------------------------------------------------------------


# /search-term-trends, /close-variants moved to routers/analytics/_waste.py


# ---------------------------------------------------------------------------
# A3: Conversion Tracking Health
# ---------------------------------------------------------------------------


# /conversion-health moved to routers/analytics/_quality.py


# ---------------------------------------------------------------------------
# G2: Keyword Expansion Suggestions
# ---------------------------------------------------------------------------


# /keyword-expansion moved to routers/analytics/_waste.py


# ---------------------------------------------------------------------------
# GAP 1B: Smart Bidding Health
# ---------------------------------------------------------------------------

# /smart-bidding-health moved to routers/analytics/_bidding.py


# ---------------------------------------------------------------------------
# GAP 7A: Pareto 80/20 Analysis
# ---------------------------------------------------------------------------

# /pareto-analysis + /scaling-opportunities + /change-impact moved to _insights.py


# Bidding endpoints (/bid-strategy-impact, /ad-group-health, /target-vs-actual,
# /bid-strategy-report, /learning-status, /portfolio-health) moved to routers/analytics/_bidding.py


# ---------------------------------------------------------------------------
# GAP 2A-2D: Conversion Data Quality Audit
# ---------------------------------------------------------------------------

# /conversion-quality moved to routers/analytics/_quality.py


# ---------------------------------------------------------------------------
# GAP 4A: Demographic Breakdown (Age/Gender)
# ---------------------------------------------------------------------------

# /demographics moved to routers/analytics/_breakdown.py


# ---------------------------------------------------------------------------
# PMax endpoints moved to routers/analytics/_pmax.py


# /placement-exclusion, /placement-performance, /shopping-product-groups (tree)
# moved to routers/analytics/_shopping.py


# Auction endpoints moved to routers/analytics/_auction.py


# MCC + misc endpoints moved to routers/analytics/_mcc_misc.py


# ---------------------------------------------------------------------------
# G4: Cross-Campaign Analysis — keyword overlap, budget allocation, comparison
# ---------------------------------------------------------------------------


# /keyword-overlap, /budget-allocation moved to routers/analytics/_waste.py


# Comparison + benchmarks endpoints moved to routers/analytics/_comparison.py
# DSA endpoints moved to routers/analytics/_dsa.py
