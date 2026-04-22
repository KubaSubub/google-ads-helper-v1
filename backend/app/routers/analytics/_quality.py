"""Quality analysis — RSA, n-grams, match types, landing pages, conversion
tracking health + conversion quality audit + full Quality Score audit."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdGroup, Campaign, Client, Keyword, KeywordDaily
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates
from app.utils.formatters import micros_to_currency
from app.utils.quality_score import (
    build_recommendation,
    build_subcomponent_issues,
    get_primary_issue,
)

router = APIRouter()


@router.get("/quality-score-audit")
def quality_score_audit(
    client_id: int = Query(...),
    qs_threshold: int = Query(5, ge=1, le=10, description="Flag keywords with QS below this"),
    campaign_id: int = Query(None, description="Filter by campaign ID"),
    match_type: str = Query(None, description="Filter by match type: EXACT, PHRASE, BROAD"),
    sort_by: str = Query("quality_score", description="Sort field"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    date_from: date = Query(None, description="Start date for cost aggregation"),
    date_to: date = Query(None, description="End date for cost aggregation"),
    db: Session = Depends(get_db),
):
    """Quality Score audit with subcomponent diagnostics."""
    query = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Keyword.status == "ENABLED",
            Keyword.quality_score.isnot(None),
            Keyword.quality_score > 0,
        )
    )
    if campaign_id is not None:
        query = query.filter(Campaign.id == campaign_id)
    if match_type is not None:
        query = query.filter(Keyword.match_type == match_type)

    keywords = query.all()

    if not keywords:
        return {
            "total_keywords": 0, "low_qs_keywords": [], "keywords": [],
            "average_qs": 0, "qs_distribution": {},
            "available_campaigns": [], "issue_breakdown": {},
        }

    all_qs = [k.quality_score for k in keywords]
    avg_qs = sum(all_qs) / len(all_qs)

    all_ag_ids = {kw.ad_group_id for kw in keywords if kw.ad_group_id}
    campaign_by_ag = {}
    campaign_id_by_ag = {}
    ag_name_by_ag = {}
    rows = []
    if all_ag_ids:
        rows = (
            db.query(AdGroup.id, AdGroup.name, Campaign.id, Campaign.name)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(AdGroup.id.in_(all_ag_ids))
            .all()
        )
        campaign_by_ag = {ag_id: cname for ag_id, ag_name, cid, cname in rows}
        campaign_id_by_ag = {ag_id: cid for ag_id, ag_name, cid, cname in rows}
        ag_name_by_ag = {ag_id: ag_name for ag_id, ag_name, cid, cname in rows}

    seen_campaigns = {}
    for ag_id, ag_name, cid, cname in rows:
        if cid not in seen_campaigns:
            seen_campaigns[cid] = cname
    available_campaigns = [{"id": cid, "name": cname} for cid, cname in seen_campaigns.items()]

    daily_agg = {}
    use_daily = date_from is not None and date_to is not None
    if use_daily:
        kw_ids = [kw.id for kw in keywords]
        if kw_ids:
            agg_rows = (
                db.query(
                    KeywordDaily.keyword_id,
                    func.sum(KeywordDaily.clicks).label("clicks"),
                    func.sum(KeywordDaily.impressions).label("impressions"),
                    func.sum(KeywordDaily.cost_micros).label("cost_micros"),
                    func.sum(KeywordDaily.conversions).label("conversions"),
                    func.sum(KeywordDaily.conversion_value_micros).label("conv_value_micros"),
                )
                .filter(
                    KeywordDaily.keyword_id.in_(kw_ids),
                    KeywordDaily.date >= date_from,
                    KeywordDaily.date <= date_to,
                )
                .group_by(KeywordDaily.keyword_id)
                .all()
            )
            for row in agg_rows:
                daily_agg[row.keyword_id] = {
                    "clicks": row.clicks or 0,
                    "impressions": row.impressions or 0,
                    "cost_micros": row.cost_micros or 0,
                    "conversions": row.conversions or 0,
                    "conv_value_micros": row.conv_value_micros or 0,
                }

    all_kw_dicts = []
    low_qs = []
    issue_counts = {"expected_ctr": 0, "ad_relevance": 0, "landing_page": 0}

    for kw in keywords:
        campaign_name = campaign_by_ag.get(kw.ad_group_id, "Unknown")
        primary_issue = get_primary_issue(kw)

        d = daily_agg.get(kw.id) if use_daily else None
        kw_clicks = d["clicks"] if d else (kw.clicks or 0)
        kw_impressions = d["impressions"] if d else (kw.impressions or 0)
        kw_cost_micros = d["cost_micros"] if d else (kw.cost_micros or 0)
        kw_conversions = d["conversions"] if d else (kw.conversions or 0)
        kw_conv_value_micros = d["conv_value_micros"] if d else (kw.conversion_value_micros or 0)
        kw_ctr = round((kw_clicks / kw_impressions * 100) if kw_impressions > 0 else 0, 2) if use_daily else round(kw.ctr or 0, 2)

        kw_dict = {
            "keyword": kw.text,
            "keyword_id": kw.id,
            "google_keyword_id": kw.google_keyword_id,
            "quality_score": kw.quality_score,
            "campaign": campaign_name,
            "campaign_id": campaign_id_by_ag.get(kw.ad_group_id),
            "ad_group": ag_name_by_ag.get(kw.ad_group_id, "Unknown"),
            "match_type": kw.match_type,
            "ctr_pct": kw_ctr,
            "clicks": kw_clicks,
            "impressions": kw_impressions,
            "cost_usd": micros_to_currency(kw_cost_micros),
            "conversions": round(kw_conversions, 1),
            "conversion_value_usd": micros_to_currency(kw_conv_value_micros),
            "ad_relevance": kw.historical_creative_quality,
            "landing_page": kw.historical_landing_page_quality,
            "expected_ctr": kw.historical_search_predicted_ctr,
            "search_impression_share": kw.search_impression_share,
            "search_rank_lost_is": kw.search_rank_lost_is,
            "serving_status": kw.serving_status,
            "primary_issue": primary_issue,
            "issues": build_subcomponent_issues(kw),
            "recommendation": build_recommendation(kw),
        }
        all_kw_dicts.append(kw_dict)

        if kw.quality_score < qs_threshold:
            low_qs.append(kw_dict)

        if primary_issue and primary_issue in issue_counts:
            issue_counts[primary_issue] += 1

    reverse = sort_dir == "desc"
    sort_key = sort_by if sort_by in ("quality_score", "clicks", "impressions", "ctr_pct") else "quality_score"
    all_kw_dicts.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)
    low_qs.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    def _kw_cost(kw):
        if use_daily:
            d = daily_agg.get(kw.id)
            return d["cost_micros"] if d else 0
        return kw.cost_micros or 0
    low_spend = sum(_kw_cost(kw) for kw in keywords if kw.quality_score < qs_threshold)
    total_spend = sum(_kw_cost(kw) for kw in keywords)
    rank_lost_vals = [kw.search_rank_lost_is for kw in keywords if kw.search_rank_lost_is is not None]
    high_qs_count = sum(1 for q in all_qs if q >= 8)

    client_obj = db.get(Client, client_id)
    google_customer_id = client_obj.google_customer_id if client_obj else None

    return {
        "total_keywords": len(keywords),
        "google_customer_id": google_customer_id,
        "average_qs": round(avg_qs, 1),
        "low_qs_count": len(low_qs),
        "high_qs_count": high_qs_count,
        "qs_threshold": qs_threshold,
        "low_qs_spend_usd": micros_to_currency(low_spend),
        "low_qs_spend_pct": round(low_spend / total_spend * 100, 1) if total_spend > 0 else 0,
        "avg_rank_lost_is": round(sum(rank_lost_vals) / len(rank_lost_vals) * 100, 1) if rank_lost_vals else None,
        "issue_breakdown": issue_counts,
        "available_campaigns": available_campaigns,
        "qs_distribution": {
            f"qs_{i}": sum(1 for q in all_qs if q == i)
            for i in range(1, 11)
        },
        "keywords": all_kw_dicts,
        "low_qs_keywords": low_qs,
    }


@router.get("/rsa-analysis")
def get_rsa_analysis(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """RSA ad performance comparison per ad group."""
    service = AnalyticsService(db)
    return service.get_rsa_analysis(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/ngram-analysis")
def get_ngram_analysis(
    client_id: int = Query(..., description="Client ID"),
    ngram_size: int = Query(1, ge=1, le=3, description="1=words, 2=bigrams, 3=trigrams"),
    min_occurrences: int = Query(2, ge=1, description="Min occurrences to include"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Search term word/n-gram aggregation by performance."""
    service = AnalyticsService(db)
    return service.get_ngram_analysis(
        client_id=client_id, ngram_size=ngram_size, min_occurrences=min_occurrences,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/match-type-analysis")
def get_match_type_analysis(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword performance comparison by match type."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_match_type_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/landing-pages")
def get_landing_pages(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword metrics aggregated by landing page URL."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_landing_page_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/landing-page-diagnostics")
def landing_page_diagnostics(
    client_id: int = Query(..., description="Client ID"),
    severity: str = Query("ALL", description="HIGH / MEDIUM / LOW / ALL"),
    db: Session = Depends(get_db),
):
    """Per-LP diagnostic flags — LP experience QS component, CVR vs account avg,
    message-match risk (many ad groups → one LP), tracking template complexity.
    """
    from app.services.landing_page_service import landing_page_report

    items = landing_page_report(db, client_id)
    if severity != "ALL":
        items = [i for i in items if i["severity"] == severity.upper()]
    return {"total": len(items), "items": items}


@router.get("/conversion-health")
def get_conversion_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Conversion tracking health audit per campaign."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_conversion_tracking_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/conversion-quality")
def get_conversion_quality(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Audit conversion action configuration for data quality issues."""
    service = AnalyticsService(db)
    return service.get_conversion_quality_audit(client_id=client_id)
