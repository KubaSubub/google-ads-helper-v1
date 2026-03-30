"""Campaign endpoints: list, detail, update, and metrics."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.demo_guard import ensure_demo_write_allowed
from app.database import get_db
from app.models import AdGroup, Campaign, Client, MetricDaily
from app.schemas import CampaignResponse, CampaignUpdate, MetricDailyResponse, PaginatedResponse
from app.services.campaign_roles import apply_manual_role_override, ensure_campaign_roles

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("/", response_model=PaginatedResponse)
def list_campaigns(
    client_id: int = Query(..., description="Filter by client ID"),
    status: str = Query(None, description="Filter by status: ENABLED, PAUSED, REMOVED"),
    campaign_type: str = Query(None, description="Filter by type: SEARCH, DISPLAY, etc."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List campaigns for a client with filtering and pagination."""
    query = db.query(Campaign).filter(Campaign.client_id == client_id)

    if status:
        query = query.filter(Campaign.status == status.upper())
    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type.upper())

    total = query.count()
    items = query.order_by(Campaign.name).offset((page - 1) * page_size).limit(page_size).all()

    client = db.get(Client, client_id)
    if items and client and ensure_campaign_roles(items, client):
        db.commit()
        for item in items:
            db.refresh(item)

    return PaginatedResponse(
        items=[CampaignResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a single campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    client = db.get(Client, campaign.client_id)
    if client and ensure_campaign_roles([campaign], client):
        db.commit()
        db.refresh(campaign)

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Patch campaign role override metadata."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    client = db.get(Client, campaign.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Edycja ustawien kampanii",
    )

    if "campaign_role_final" in data.model_fields_set:
        final_role = data.campaign_role_final.value if data.campaign_role_final is not None else None
        apply_manual_role_override(campaign, final_role, client)

    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}/metrics", response_model=list[MetricDailyResponse])
def get_campaign_metrics(
    campaign_id: int,
    date_from: date = Query(None, description="Start date (default: 30 days ago)"),
    date_to: date = Query(None, description="End date (default: today)"),
    db: Session = Depends(get_db),
):
    """Get daily metrics for a campaign within a date range."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    metrics = (
        db.query(MetricDaily)
        .filter(
            MetricDaily.campaign_id == campaign_id,
            MetricDaily.date >= date_from,
            MetricDaily.date <= date_to,
        )
        .order_by(MetricDaily.date)
        .all()
    )
    return metrics


@router.get("/{campaign_id}/kpis")
def get_campaign_kpis(
    campaign_id: int,
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Get aggregated KPIs for a campaign for the current period vs the previous period."""
    from app.utils.date_utils import resolve_dates
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_start, today = resolve_dates(days, date_from, date_to)
    period_len = (today - current_start).days
    previous_start = current_start - timedelta(days=period_len)

    def _aggregate(start: date, end: date) -> dict:
        metrics = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id == campaign_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        if not metrics:
            return {
                "clicks": 0,
                "impressions": 0,
                "cost": 0,
                "conversions": 0,
                "conversion_value": 0,
                "ctr": 0,
                "roas": 0,
                "avg_cpc": 0,
                "cpa": 0,
                "conversion_rate": 0,
                "search_impression_share": None,
                "search_top_impression_share": None,
                "search_abs_top_impression_share": None,
                "search_budget_lost_is": None,
                "search_rank_lost_is": None,
                "search_click_share": None,
                "abs_top_impression_pct": None,
                "top_impression_pct": None,
            }

        total_clicks = sum(m.clicks or 0 for m in metrics)
        total_impressions = sum(m.impressions or 0 for m in metrics)
        total_cost_micros = sum(m.cost_micros or 0 for m in metrics)
        total_conversions = sum(m.conversions or 0 for m in metrics)
        total_conv_value_micros = sum(m.conversion_value_micros or 0 for m in metrics)
        total_cost_usd = total_cost_micros / 1_000_000
        total_conv_value = total_conv_value_micros / 1_000_000

        def _avg_nonnull(field):
            vals = [getattr(m, field) for m in metrics if getattr(m, field) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost": round(total_cost_usd, 2),
            "conversions": total_conversions,
            "conversion_value": round(total_conv_value, 2),
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": round((total_conv_value / total_cost_usd) if total_cost_usd else 0, 2),
            "avg_cpc": round((total_cost_usd / total_clicks) if total_clicks else 0, 2),
            "cpa": round((total_cost_usd / total_conversions) if total_conversions else 0, 2),
            "conversion_rate": round((total_conversions / total_clicks * 100) if total_clicks else 0, 2),
            "search_impression_share": _avg_nonnull("search_impression_share"),
            "search_top_impression_share": _avg_nonnull("search_top_impression_share"),
            "search_abs_top_impression_share": _avg_nonnull("search_abs_top_impression_share"),
            "search_budget_lost_is": _avg_nonnull("search_budget_lost_is"),
            "search_rank_lost_is": _avg_nonnull("search_rank_lost_is"),
            "search_click_share": _avg_nonnull("search_click_share"),
            "abs_top_impression_pct": _avg_nonnull("abs_top_impression_pct"),
            "top_impression_pct": _avg_nonnull("top_impression_pct"),
        }

    current = _aggregate(current_start, today)
    previous = _aggregate(previous_start, current_start - timedelta(days=1))

    def _pct_change(curr, prev):
        if curr is None or prev is None:
            return None
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round((curr - prev) / prev * 100, 1)

    change = {k: _pct_change(current[k], previous[k]) for k in current}

    return {
        "current": current,
        "previous": previous,
        "change_pct": change,
        "period_days": days,
    }


@router.patch("/{campaign_id}/bidding-target")
def update_bidding_target(
    campaign_id: int,
    field: str = Query(..., description="target_cpa_micros or target_roas"),
    value: float = Query(..., description="New value (micros for CPA, float for ROAS)"),
    allow_demo_write: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Update campaign bidding target (target CPA or target ROAS).

    Remote-first: tries API push first, commits locally only on success.
    If API is not connected, falls back to local write with pending_sync warning.
    Goes through canonical safety pipeline: demo guard → audit log.
    """
    from app.services.google_ads import google_ads_service
    from app.services.write_safety import record_write_action
    import logging

    if field not in ("target_cpa_micros", "target_roas"):
        raise HTTPException(status_code=400, detail="field must be target_cpa_micros or target_roas")

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    client = db.get(Client, campaign.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db, client.id, allow_demo_write=allow_demo_write,
        operation="Zmiana celu licytacji kampanii",
    )

    old_value = getattr(campaign, field)
    new_value = int(value) if field == "target_cpa_micros" else float(value)
    api_synced = False
    api_error = None

    # Remote-first: push to Google Ads API before committing locally
    if google_ads_service.is_connected:
        try:
            google_ads_service._mutate_campaign_bidding_target(campaign, db, field, value)
            api_synced = True
        except Exception as e:
            api_error = str(e)
            logging.getLogger(__name__).warning(
                f"Bidding target API push failed for campaign {campaign_id}: {e}"
            )
            # Audit the failed attempt
            record_write_action(
                db,
                client_id=client.id,
                action_type="UPDATE_BIDDING_TARGET",
                entity_type="campaign",
                entity_id=campaign_id,
                status="FAILED",
                execution_mode="LIVE",
                old_value={field: old_value},
                new_value={field: new_value},
                error_message=api_error,
            )
            db.commit()
            raise HTTPException(
                status_code=502,
                detail=f"Google Ads API rejected the change: {api_error}. Local DB NOT updated.",
            )

    # Update local DB only after API confirmation (or if API not connected)
    setattr(campaign, field, new_value)

    # Audit trail
    record_write_action(
        db,
        client_id=client.id,
        action_type="UPDATE_BIDDING_TARGET",
        entity_type="campaign",
        entity_id=campaign_id,
        status="SUCCESS",
        execution_mode="LIVE" if api_synced else "LOCAL",
        old_value={field: old_value},
        new_value={field: new_value},
        context={"api_synced": api_synced},
    )
    db.commit()
    db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "field": field,
        "old_value": old_value,
        "new_value": getattr(campaign, field),
        "api_synced": api_synced,
        "api_error": api_error,
        "pending_sync": not api_synced,
    }
