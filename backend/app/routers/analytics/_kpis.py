"""Dashboard KPIs — /kpis, /dashboard-kpis (with period-over-period cache),
/trends, /campaign-trends, /wow-comparison, /campaigns-summary."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CommonFilters, common_filters
from app.models import Campaign, MetricDaily
from app.routers.analytics._legacy import TREND_METRICS
from app.services.analytics_service import AnalyticsService
from app.services.cache import dashboard_kpis_cache
from app.utils.date_utils import resolve_dates
from app.utils.formatters import micros_to_currency

router = APIRouter()


@router.get("/kpis")
def get_kpis(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Aggregate KPIs across all campaigns for a client."""
    service = AnalyticsService(db)
    return service.get_kpis(client_id)


@router.get("/dashboard-kpis")
def dashboard_kpis(
    filters: CommonFilters = Depends(common_filters),
    db: Session = Depends(get_db),
):
    """Aggregated KPIs with period-over-period comparison."""
    if filters.client_id is None:
        raise HTTPException(status_code=400, detail="client_id is required")
    client_id = filters.client_id
    current_start, today = filters.date_from, filters.date_to
    period_len = (today - current_start).days
    previous_start = current_start - timedelta(days=period_len)

    cache_key = (
        f"client={client_id}|dashboard-kpis"
        f"|from={current_start.isoformat()}|to={today.isoformat()}"
        f"|ctype={filters.campaign_type or ''}|cstatus={filters.campaign_status or ''}"
    )
    cached = dashboard_kpis_cache.get(cache_key)
    if cached is not None:
        return cached

    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(
        client_id,
        filters.campaign_type,
        filters.campaign_status,
    )
    if not campaign_ids:
        empty_payload = {"current": {}, "previous": {}, "change_pct": {}}
        dashboard_kpis_cache[cache_key] = empty_payload
        return empty_payload

    active_campaigns = (
        db.query(func.count(Campaign.id))
        .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
        .scalar()
    ) or 0

    def _agg(start: date, end: date) -> dict:
        rows = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        empty = {
            "clicks": 0, "impressions": 0, "cost_usd": 0, "conversions": 0,
            "ctr": 0, "roas": 0, "cpa": 0, "conversion_value_usd": 0,
            "cvr": 0, "avg_cpc_usd": 0, "all_conversions": 0,
            "all_conversions_value_usd": 0, "cross_device_conversions": 0,
            "value_per_conversion_usd": 0,
            "search_impression_share": None, "search_top_impression_share": None,
            "search_abs_top_impression_share": None,
            "search_budget_lost_is": None, "search_rank_lost_is": None,
            "search_click_share": None,
            "abs_top_impression_pct": None, "top_impression_pct": None,
            "active_campaigns": active_campaigns,
        }
        if not rows:
            return empty

        total_clicks = sum(r.clicks or 0 for r in rows)
        total_impressions = sum(r.impressions or 0 for r in rows)
        total_cost_micros = sum(r.cost_micros or 0 for r in rows)
        total_conversions = sum(r.conversions or 0 for r in rows)
        total_conv_value_micros = sum(r.conversion_value_micros or 0 for r in rows)
        total_all_conversions = sum(r.all_conversions or 0 for r in rows)
        total_all_conv_value_micros = sum(r.all_conversions_value_micros or 0 for r in rows)
        total_cross_device = sum(r.cross_device_conversions or 0 for r in rows)

        total_cost_usd = micros_to_currency(total_cost_micros)
        total_conv_value_usd = micros_to_currency(total_conv_value_micros)
        total_all_conv_value_usd = micros_to_currency(total_all_conv_value_micros)
        # ROAS: distinguish "value not tracked" (conversions > 0 but conv_value = 0 → None)
        # from "value tracked, actual zero return" (conversions = 0 → 0).
        # Prevents false "low ROAS" alerts on accounts that never configured conversion values.
        if not total_cost_usd:
            roas = None
        elif total_conversions > 0 and total_conv_value_micros == 0:
            roas = None
        else:
            roas = round(total_conv_value_usd / total_cost_usd, 2)
        cpa = round((total_cost_usd / total_conversions) if total_conversions else 0, 2)
        cvr = round((total_conversions / total_clicks * 100) if total_clicks else 0, 2)
        avg_cpc_usd = round((total_cost_usd / total_clicks) if total_clicks else 0, 2)
        vpc_usd = round((total_conv_value_usd / total_conversions) if total_conversions else 0, 2)

        def _weighted_avg(attr):
            pairs = [(getattr(r, attr), r.impressions or 0) for r in rows if getattr(r, attr) is not None]
            if not pairs:
                return None
            total_w = sum(w for _, w in pairs)
            if total_w == 0:
                return None
            return round(sum(v * w for v, w in pairs) / total_w, 4)

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost_usd": total_cost_usd,
            "conversions": total_conversions,
            "conversion_value_usd": total_conv_value_usd,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": roas,
            "cpa": cpa,
            "cvr": cvr,
            "avg_cpc_usd": avg_cpc_usd,
            "all_conversions": round(total_all_conversions, 2),
            "all_conversions_value_usd": round(total_all_conv_value_usd, 2),
            "cross_device_conversions": round(total_cross_device, 2),
            "value_per_conversion_usd": vpc_usd,
            "search_impression_share": _weighted_avg("search_impression_share"),
            "search_top_impression_share": _weighted_avg("search_top_impression_share"),
            "search_abs_top_impression_share": _weighted_avg("search_abs_top_impression_share"),
            "search_budget_lost_is": _weighted_avg("search_budget_lost_is"),
            "search_rank_lost_is": _weighted_avg("search_rank_lost_is"),
            "search_click_share": _weighted_avg("search_click_share"),
            "abs_top_impression_pct": _weighted_avg("abs_top_impression_pct"),
            "top_impression_pct": _weighted_avg("top_impression_pct"),
            "active_campaigns": active_campaigns,
        }

    current = _agg(current_start, today)
    previous = _agg(previous_start, current_start - timedelta(days=1))

    def _pct(c, p):
        if c is None or p is None:
            return None
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)

    change = {k: _pct(current[k], previous[k]) for k in current}

    payload = {"current": current, "previous": previous, "change_pct": change, "period_days": period_len}
    dashboard_kpis_cache[cache_key] = payload
    return payload


@router.get("/trends")
def get_trends(
    client_id: int = Query(..., description="Client ID"),
    metrics: str = Query("cost,clicks", description="Comma-separated metrics from TREND_METRICS"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL", description="ALL | SEARCH | PERFORMANCE_MAX | DISPLAY | SHOPPING"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query("ALL", description="Alias for campaign_status (backward compat)"),
    campaign_ids: str = Query(None, description="Comma-separated campaign IDs — restrict aggregation to these"),
    db: Session = Depends(get_db),
):
    """Daily aggregated metrics for TrendExplorer chart."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)

    max_span = timedelta(days=365)
    if end - start > max_span:
        start = end - max_span

    metric_list = [m.strip() for m in metrics.split(",") if m.strip() in TREND_METRICS]
    if not metric_list:
        metric_list = ["cost", "clicks"]

    id_filter: list[int] | None = None
    if campaign_ids:
        try:
            id_filter = [int(x) for x in campaign_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    service = AnalyticsService(db)
    return service.get_trends(
        client_id=client_id,
        metrics=metric_list,
        date_from=start,
        date_to=end,
        campaign_type=campaign_type,
        campaign_status=effective_status,
        campaign_ids=id_filter,
    )


@router.get("/campaign-trends")
def get_campaign_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=3, le=90, description="Trend window in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Per-campaign cost trend for sparkline display in campaigns table."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_campaign_trends(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


@router.get("/wow-comparison")
def wow_comparison(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=7, le=30, description="Period length (default 7 = week)"),
    date_from: date = Query(None, description="End of current period (overrides days)"),
    date_to: date = Query(None, description="End of current period"),
    metric: str = Query("cost", description="Metric: cost,clicks,impressions,conversions,ctr,cpc,roas,cpa"),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    status: str = Query("ALL"),
    db: Session = Depends(get_db),
):
    """Current period vs previous period with day-of-week alignment for overlay chart."""
    effective_status = campaign_status or status
    current_end = date_to or date.today()
    current_start = date_from or (current_end - timedelta(days=days - 1))
    period_len = (current_end - current_start).days + 1

    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_len - 1)

    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(client_id, campaign_type, effective_status)
    if not campaign_ids:
        return {"current": [], "previous": [], "metric": metric}

    allowed = {"cost", "clicks", "impressions", "conversions", "ctr", "cpc", "roas", "cpa"}
    if metric not in allowed:
        metric = "cost"

    def _aggregate(start: date, end: date) -> list[dict]:
        rows = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        day_map: dict[date, dict] = {}
        for r in rows:
            d = r.date
            if d not in day_map:
                day_map[d] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                              "conversions": 0.0, "conv_value_micros": 0}
            day_map[d]["clicks"] += r.clicks or 0
            day_map[d]["impressions"] += r.impressions or 0
            day_map[d]["cost_micros"] += r.cost_micros or 0
            day_map[d]["conversions"] += r.conversions or 0
            day_map[d]["conv_value_micros"] += r.conversion_value_micros or 0

        result = []
        for d in sorted(day_map.keys()):
            agg = day_map[d]
            clicks = agg["clicks"]
            impressions = agg["impressions"]
            cost_usd = agg["cost_micros"] / 1_000_000
            conversions = agg["conversions"]
            conv_value_usd = agg["conv_value_micros"] / 1_000_000

            values = {
                "cost": round(cost_usd, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 1),
                "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
                "cpc": round(cost_usd / clicks, 2) if clicks else 0,
                "roas": round(conv_value_usd / cost_usd, 2) if cost_usd else 0,
                "cpa": round(cost_usd / conversions, 2) if conversions else 0,
            }
            DOW_LABELS = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
            result.append({
                "date": str(d),
                "dow": DOW_LABELS[d.weekday()],
                "day_index": (d - start).days,
                "value": values.get(metric, 0),
            })
        return result

    return {
        "metric": metric,
        "period_days": period_len,
        "current_range": [str(current_start), str(current_end)],
        "previous_range": [str(previous_start), str(previous_end)],
        "current": _aggregate(current_start, current_end),
        "previous": _aggregate(previous_start, previous_end),
    }


@router.get("/campaigns-summary")
def campaigns_summary(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=365),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    status: str = Query("ALL", description="Alias for campaign_status"),
    db: Session = Depends(get_db),
):
    """Per-campaign aggregated metrics (clicks, cost, conversions, roas) for a period."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)
    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(client_id, campaign_type, effective_status)
    if not campaign_ids:
        return {"campaigns": {}}

    rows = (
        db.query(
            MetricDaily.campaign_id,
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
        )
        .filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= start,
            MetricDaily.date <= end,
        )
        .group_by(MetricDaily.campaign_id)
        .all()
    )

    is_map = {}
    camp_rows = db.query(Campaign.id, Campaign.search_impression_share).filter(Campaign.id.in_(campaign_ids)).all()
    for cr in camp_rows:
        is_map[cr.id] = cr.search_impression_share

    result = {}
    for r in rows:
        cost_usd = micros_to_currency(r.cost_micros or 0)
        conv_value_usd = micros_to_currency(r.conv_value_micros or 0)
        clicks = r.clicks or 0
        impressions = r.impressions or 0
        conversions = r.conversions or 0
        result[str(r.campaign_id)] = {
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": round(cost_usd, 2),
            "conversions": round(conversions, 1),
            "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
            "roas": round(conv_value_usd / cost_usd, 2) if cost_usd else 0,
            "impression_share": is_map.get(r.campaign_id),
        }

    return {"campaigns": result}
