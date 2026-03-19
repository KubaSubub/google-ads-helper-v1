"""Client CRUD endpoints."""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.demo_guard import ensure_demo_write_allowed, is_demo_protected_client
from app.database import get_db
from app.models import (
    AdGroup,
    Ad,
    ActionLog,
    Alert,
    Campaign,
    ChangeEvent,
    Client,
    Keyword,
    KeywordDaily,
    MetricDaily,
    MetricSegmented,
    NegativeKeyword,
    Recommendation,
    SearchTerm,
    SyncLog,
)
from app.schemas import ClientCreate, ClientResponse, ClientUpdate, PaginatedResponse
from app.services.credentials_service import CredentialsService
from app.services.google_ads import google_ads_service

router = APIRouter(prefix="/clients", tags=["Clients"])


def _ensure_discover_ready() -> None:
    diagnostics = google_ads_service.get_connection_diagnostics()
    if not diagnostics["configured"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not diagnostics["authenticated"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not diagnostics["ready"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not CredentialsService.get(CredentialsService.LOGIN_CUSTOMER_ID):
        raise HTTPException(
            status_code=503,
            detail="Brak login_customer_id (MCC). Uzupelnij Login Customer ID w konfiguracji API.",
        )


def _hard_reset_client_runtime_data(db: Session, client: Client) -> dict[str, int]:
    counts: dict[str, int] = {}
    direct_tables = [
        (ChangeEvent, "deleted_change_events"),
        (Alert, "deleted_alerts"),
        (ActionLog, "deleted_action_logs"),
        (SyncLog, "deleted_sync_logs"),
        (Recommendation, "deleted_recommendations"),
        (NegativeKeyword, "deleted_negative_keywords"),
    ]

    for model, key in direct_tables:
        query = db.query(model).filter(model.client_id == client.id)
        counts[key] = query.count()
        query.delete(synchronize_session=False)

    campaigns = db.query(Campaign).filter(Campaign.client_id == client.id).all()
    counts["deleted_campaigns"] = len(campaigns)
    for campaign in campaigns:
        db.delete(campaign)

    client.last_change_sync_at = None
    return counts


def _seed_demo_keyword_daily(
    db: Session,
    keywords: list[Keyword],
    days: int,
) -> dict[str, int]:
    if not keywords:
        return {"deleted_keyword_daily": 0, "seeded_keyword_daily": 0}

    keyword_ids = [kw.id for kw in keywords]
    cutoff = date.today() - timedelta(days=days - 1)
    deleted_rows = (
        db.query(KeywordDaily)
        .filter(KeywordDaily.keyword_id.in_(keyword_ids), KeywordDaily.date >= cutoff)
        .delete(synchronize_session=False)
    )

    inserted_rows = 0
    waste_positions = {1}
    if len(keywords) > 6:
        waste_positions.add(len(keywords) - 2)

    for kw_index, kw in enumerate(keywords):
        is_waste_keyword = kw_index in waste_positions
        base_daily_clicks = max(2.0, (kw.clicks or 90) / 30.0)
        base_daily_impressions = max(base_daily_clicks * 9.0, (kw.impressions or 1500) / 30.0)
        base_daily_cost_micros = max(base_daily_clicks * 350_000, (kw.cost_micros or 120_000_000) / 30.0)
        base_daily_conversions = max(0.0, float(kw.conversions or 6.0) / 30.0)
        conv_rate = 0.0 if is_waste_keyword else min(0.25, max(0.01, base_daily_conversions / max(base_daily_clicks, 1.0)))

        for day_index in range(days):
            current_day = cutoff + timedelta(days=day_index)
            weekday = current_day.weekday()
            weekday_factor = 1.08 if weekday in (1, 2, 3) else (0.86 if weekday >= 5 else 0.98)
            trend_factor = 0.92 + (day_index / max(days - 1, 1)) * 0.22
            keyword_factor = 0.88 + (kw.id % 7) * 0.045
            wave_factor = 1.0 + ((day_index % 6) - 2) * 0.02
            multiplier = max(0.55, weekday_factor * trend_factor * keyword_factor * wave_factor)

            clicks = max(1, int(base_daily_clicks * multiplier))
            impressions = max(clicks * 8, int(base_daily_impressions * multiplier))
            cost_micros = max(clicks * 280_000, int(base_daily_cost_micros * multiplier))
            if is_waste_keyword and day_index % 2 == 0:
                cost_micros = int(cost_micros * 1.22)

            if conv_rate <= 0:
                conversions = 0.0
                conversion_value_micros = 0
            else:
                conversions = round(clicks * conv_rate, 2)
                conversion_value_micros = max(
                    int(cost_micros * (2.1 + (kw.id % 5) * 0.24)),
                    int(conversions * 38_000_000),
                )

            db.add(
                KeywordDaily(
                    keyword_id=kw.id,
                    date=current_day,
                    clicks=clicks,
                    impressions=impressions,
                    cost_micros=cost_micros,
                    conversions=conversions,
                    conversion_value_micros=conversion_value_micros,
                    avg_cpc_micros=int(cost_micros / max(clicks, 1)),
                )
            )
            inserted_rows += 1

    return {
        "deleted_keyword_daily": int(deleted_rows or 0),
        "seeded_keyword_daily": inserted_rows,
        "seeded_waste_keywords": len(waste_positions),
    }


def _seed_demo_ads(
    db: Session,
    client: Client,
    ad_groups: list[AdGroup],
    keywords_by_ad_group: dict[int, list[Keyword]],
) -> dict[str, int]:
    if not ad_groups:
        return {"deleted_ads": 0, "seeded_ads": 0}

    ad_group_ids = [ag.id for ag in ad_groups]
    deleted_rows = (
        db.query(Ad)
        .filter(Ad.ad_group_id.in_(ad_group_ids))
        .delete(synchronize_session=False)
    )

    created_ads = 0
    created_waste_ads = 0
    default_url = (client.website or "https://demo-meble.pl").strip() or "https://demo-meble.pl"

    for group_index, ad_group in enumerate(ad_groups):
        group_keywords = keywords_by_ad_group.get(ad_group.id, [])
        primary_term = group_keywords[0].text if group_keywords else ad_group.name
        secondary_term = group_keywords[1].text if len(group_keywords) > 1 else ad_group.name
        final_url = (group_keywords[0].final_url if group_keywords and group_keywords[0].final_url else default_url)

        for variant in (1, 2):
            clicks = 85 + group_index * 14 + variant * 18
            impressions = clicks * (8 + variant) + group_index * 35
            ctr_pct = (clicks / impressions * 100) if impressions else 0
            cost_micros = int(clicks * (930_000 if variant == 1 else 790_000))

            is_waste_ad = variant == 2 and group_index % 3 == 0
            if is_waste_ad:
                cost_micros = int(cost_micros * 1.28)
                conversions = 0.0
                created_waste_ads += 1
            else:
                conversions = round(clicks * (0.078 if variant == 1 else 0.061), 2)

            ad = Ad(
                ad_group_id=ad_group.id,
                google_ad_id=f"demo-{ad_group.id}-{variant}",
                ad_type="RESPONSIVE_SEARCH_AD",
                status="ENABLED",
                approval_status="APPROVED",
                ad_strength="EXCELLENT" if variant == 1 else "GOOD",
                final_url=final_url,
                headlines=[
                    {"text": f"{primary_term.title()} - szybka dostawa", "pinned_position": "HEADLINE_1" if variant == 1 else None},
                    {"text": "Darmowa dostawa od 199 zl", "pinned_position": None},
                    {"text": f"Promocje: {secondary_term.lower()}", "pinned_position": None},
                    {"text": "Zwrot do 30 dni", "pinned_position": None},
                ],
                descriptions=[
                    {"text": "Sprawdz bestsellery i kup online z bezpieczna platnoscia."},
                    {"text": "Montaz i szybka wysylka na terenie calej Polski."},
                ],
                clicks=clicks,
                impressions=impressions,
                cost_micros=cost_micros,
                conversions=conversions,
                ctr=round(ctr_pct, 2),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(ad)
            created_ads += 1

    return {
        "deleted_ads": int(deleted_rows or 0),
        "seeded_ads": created_ads,
        "seeded_waste_ads": created_waste_ads,
    }


def _seed_demo_search_terms(
    db: Session,
    campaigns: list[Campaign],
    ad_groups: list[AdGroup],
    days: int,
) -> dict[str, int]:
    if not campaigns:
        return {"deleted_seeded_search_terms": 0, "seeded_search_terms": 0}

    campaign_ids = [campaign.id for campaign in campaigns]
    deleted_rows = (
        db.query(SearchTerm)
        .filter(SearchTerm.campaign_id.in_(campaign_ids), SearchTerm.text.like("[DEMO] %"))
        .delete(synchronize_session=False)
    )

    terms_templates = [
        {"text": "[DEMO] sofa uzywana tanio", "segment": "WASTE", "clicks": 26, "impressions": 940, "cost_micros": 41_000_000, "conversions": 0.0},
        {"text": "[DEMO] darmowe meble do odbioru", "segment": "WASTE", "clicks": 19, "impressions": 870, "cost_micros": 34_000_000, "conversions": 0.0},
        {"text": "[DEMO] instrukcja montazu ikea", "segment": "WASTE", "clicks": 14, "impressions": 620, "cost_micros": 27_000_000, "conversions": 0.0},
        {"text": "[DEMO] sofa modulowa premium", "segment": "HIGH_PERFORMER", "clicks": 22, "impressions": 490, "cost_micros": 24_000_000, "conversions": 2.9},
        {"text": "[DEMO] naroznik z funkcja spania", "segment": "HIGH_PERFORMER", "clicks": 31, "impressions": 760, "cost_micros": 36_000_000, "conversions": 3.8},
        {"text": "[DEMO] lozko tapicerowane 160x200", "segment": "HIGH_PERFORMER", "clicks": 28, "impressions": 690, "cost_micros": 33_000_000, "conversions": 3.2},
    ]

    ad_groups_by_campaign: dict[int, list[AdGroup]] = {}
    for ad_group in ad_groups:
        ad_groups_by_campaign.setdefault(ad_group.campaign_id, []).append(ad_group)

    inserted_rows = 0
    today = date.today()
    for index, template in enumerate(terms_templates):
        campaign = campaigns[index % len(campaigns)]
        campaign_ad_groups = ad_groups_by_campaign.get(campaign.id, [])
        ad_group = campaign_ad_groups[index % len(campaign_ad_groups)] if campaign_ad_groups else None

        date_to = today - timedelta(days=index % max(3, min(days, 14)))
        date_from = date_to - timedelta(days=6)
        clicks = template["clicks"]
        impressions = template["impressions"]
        conversions = template["conversions"]
        ctr_pct = round((clicks / max(impressions, 1)) * 100, 2)
        conversion_rate_pct = round((conversions / max(clicks, 1)) * 100, 2) if clicks else 0.0
        conversion_value_micros = int(template["cost_micros"] * (3.2 if conversions > 0 else 0.0))

        db.add(
            SearchTerm(
                ad_group_id=ad_group.id if ad_group else None,
                campaign_id=campaign.id,
                text=template["text"],
                keyword_text=(ad_group.name if ad_group else campaign.name),
                match_type="BROAD" if template["segment"] == "WASTE" else "PHRASE",
                segment=template["segment"],
                source="SEARCH",
                clicks=clicks,
                impressions=impressions,
                cost_micros=template["cost_micros"],
                conversions=conversions,
                conversion_value_micros=conversion_value_micros,
                ctr=ctr_pct,
                conversion_rate=conversion_rate_pct,
                date_from=date_from,
                date_to=date_to,
            )
        )
        inserted_rows += 1

    return {
        "deleted_seeded_search_terms": int(deleted_rows or 0),
        "seeded_search_terms": inserted_rows,
    }


def _seed_demo_action_logs(
    db: Session,
    client: Client,
    campaigns: list[Campaign],
    keywords: list[Keyword],
) -> dict[str, int]:
    deleted_seeded = (
        db.query(ActionLog)
        .filter(ActionLog.client_id == client.id, ActionLog.execution_mode == "DEMO_SEED")
        .delete(synchronize_session=False)
    )

    if not campaigns or not keywords:
        return {"deleted_seeded_actions": int(deleted_seeded or 0), "seeded_actions": 0}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    keyword_ids = [kw.id for kw in keywords[:6]]
    campaign_ids = [c.id for c in campaigns[:2]]

    action_templates = [
        {
            "action_type": "UPDATE_BID",
            "entity_type": "keyword",
            "entity_id": str(keyword_ids[0]),
            "old": {"bid_micros": 1200000},
            "new": {"bid_micros": 1500000},
            "days_ago": 1,
        },
        {
            "action_type": "UPDATE_BID",
            "entity_type": "keyword",
            "entity_id": str(keyword_ids[1 % len(keyword_ids)]),
            "old": {"bid_micros": 950000},
            "new": {"bid_micros": 1150000},
            "days_ago": 2,
        },
        {
            "action_type": "PAUSE_KEYWORD",
            "entity_type": "keyword",
            "entity_id": str(keyword_ids[2 % len(keyword_ids)]),
            "old": {"status": "ENABLED"},
            "new": {"status": "PAUSED"},
            "days_ago": 3,
        },
        {
            "action_type": "SET_CAMPAIGN_BUDGET",
            "entity_type": "campaign",
            "entity_id": str(campaign_ids[0]),
            "old": {"budget_micros": 180000000},
            "new": {"budget_micros": 220000000},
            "days_ago": 4,
        },
        {
            "action_type": "SET_CAMPAIGN_BUDGET",
            "entity_type": "campaign",
            "entity_id": str(campaign_ids[1 % len(campaign_ids)]),
            "old": {"budget_micros": 140000000},
            "new": {"budget_micros": 160000000},
            "days_ago": 5,
        },
        {
            "action_type": "ADD_NEGATIVE",
            "entity_type": "keyword",
            "entity_id": str(keyword_ids[3 % len(keyword_ids)]),
            "old": {"negative": False},
            "new": {"negative": True},
            "days_ago": 6,
        },
    ]

    inserted = 0
    for index, item in enumerate(action_templates):
        db.add(
            ActionLog(
                client_id=client.id,
                recommendation_id=None,
                action_type=item["action_type"],
                entity_type=item["entity_type"],
                entity_id=item["entity_id"],
                old_value_json=json.dumps(item["old"], ensure_ascii=True),
                new_value_json=json.dumps(item["new"], ensure_ascii=True),
                status="SUCCESS",
                error_message=None,
                execution_mode="DEMO_SEED",
                precondition_status="PASSED",
                context_json={"source": "demo_showcase_seed", "index": index + 1},
                action_payload={"source": "demo_showcase_seed"},
                reverted_at=None,
                executed_at=now - timedelta(days=item["days_ago"], hours=(index % 3) * 2),
            )
        )
        inserted += 1

    return {
        "deleted_seeded_actions": int(deleted_seeded or 0),
        "seeded_actions": inserted,
    }


def _seed_demo_showcase_data(
    db: Session,
    client: Client,
    days: int,
) -> dict[str, int]:
    search_campaigns = (
        db.query(Campaign)
        .filter(Campaign.client_id == client.id, Campaign.campaign_type == "SEARCH")
        .order_by(Campaign.id)
        .all()
    )
    campaign_ids = [c.id for c in search_campaigns]

    ad_groups = (
        db.query(AdGroup)
        .filter(AdGroup.campaign_id.in_(campaign_ids))
        .order_by(AdGroup.id)
        .all()
    ) if campaign_ids else []
    ad_group_ids = [ag.id for ag in ad_groups]

    keywords = (
        db.query(Keyword)
        .filter(Keyword.ad_group_id.in_(ad_group_ids), Keyword.status != "REMOVED")
        .order_by(Keyword.id)
        .all()
    ) if ad_group_ids else []

    keywords_by_ad_group: dict[int, list[Keyword]] = {}
    for keyword in keywords:
        keywords_by_ad_group.setdefault(keyword.ad_group_id, []).append(keyword)

    keyword_daily_counts = _seed_demo_keyword_daily(db, keywords=keywords, days=days)
    ads_counts = _seed_demo_ads(
        db,
        client=client,
        ad_groups=ad_groups,
        keywords_by_ad_group=keywords_by_ad_group,
    )
    action_counts = _seed_demo_action_logs(
        db,
        client=client,
        campaigns=search_campaigns,
        keywords=keywords,
    )
    search_term_counts = _seed_demo_search_terms(
        db,
        campaigns=search_campaigns,
        ad_groups=ad_groups,
        days=days,
    )

    return {
        "seed_days": days,
        "seed_campaigns": len(search_campaigns),
        "seed_ad_groups": len(ad_groups),
        "seed_keywords": len(keywords),
        **keyword_daily_counts,
        **ads_counts,
        **action_counts,
        **search_term_counts,
    }


def _clone_row(model, source_obj, *, exclude: set[str] | None = None, overrides: dict | None = None):
    exclude = exclude or set()
    payload = {}
    for column in model.__table__.columns:
        key = column.name
        if key == "id" or key in exclude:
            continue
        payload[key] = getattr(source_obj, key)
    if overrides:
        payload.update(overrides)
    return model(**payload)


def _clone_runtime_data_between_clients(
    db: Session,
    source_client: Client,
    target_client: Client,
) -> dict[str, int]:
    counts = _hard_reset_client_runtime_data(db, target_client)

    campaign_map: dict[int, int] = {}
    ad_group_map: dict[int, int] = {}
    keyword_map: dict[int, int] = {}
    action_log_map: dict[int, int] = {}

    source_campaigns = db.query(Campaign).filter(Campaign.client_id == source_client.id).all()
    for src in source_campaigns:
        new_campaign = _clone_row(Campaign, src, overrides={"client_id": target_client.id})
        db.add(new_campaign)
        db.flush()
        campaign_map[src.id] = new_campaign.id
    counts["cloned_campaigns"] = len(campaign_map)

    source_ad_groups = (
        db.query(AdGroup)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == source_client.id)
        .all()
    )
    for src in source_ad_groups:
        mapped_campaign_id = campaign_map.get(src.campaign_id)
        if not mapped_campaign_id:
            continue
        new_ad_group = _clone_row(AdGroup, src, overrides={"campaign_id": mapped_campaign_id})
        db.add(new_ad_group)
        db.flush()
        ad_group_map[src.id] = new_ad_group.id
    counts["cloned_ad_groups"] = len(ad_group_map)

    source_keywords = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == source_client.id)
        .all()
    )
    for src in source_keywords:
        mapped_ad_group_id = ad_group_map.get(src.ad_group_id)
        if not mapped_ad_group_id:
            continue
        new_keyword = _clone_row(Keyword, src, overrides={"ad_group_id": mapped_ad_group_id})
        db.add(new_keyword)
        db.flush()
        keyword_map[src.id] = new_keyword.id
    counts["cloned_keywords"] = len(keyword_map)

    source_keyword_daily = (
        db.query(KeywordDaily)
        .join(Keyword, KeywordDaily.keyword_id == Keyword.id)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == source_client.id)
        .all()
    )
    cloned_keyword_daily = 0
    for src in source_keyword_daily:
        mapped_keyword_id = keyword_map.get(src.keyword_id)
        if not mapped_keyword_id:
            continue
        db.add(_clone_row(KeywordDaily, src, overrides={"keyword_id": mapped_keyword_id}))
        cloned_keyword_daily += 1
    counts["cloned_keyword_daily"] = cloned_keyword_daily

    source_metric_daily = (
        db.query(MetricDaily)
        .join(Campaign, MetricDaily.campaign_id == Campaign.id)
        .filter(Campaign.client_id == source_client.id)
        .all()
    )
    cloned_metric_daily = 0
    for src in source_metric_daily:
        mapped_campaign_id = campaign_map.get(src.campaign_id)
        if not mapped_campaign_id:
            continue
        db.add(_clone_row(MetricDaily, src, overrides={"campaign_id": mapped_campaign_id}))
        cloned_metric_daily += 1
    counts["cloned_metric_daily"] = cloned_metric_daily

    source_metric_segmented = (
        db.query(MetricSegmented)
        .join(Campaign, MetricSegmented.campaign_id == Campaign.id)
        .filter(Campaign.client_id == source_client.id)
        .all()
    )
    cloned_metric_segmented = 0
    for src in source_metric_segmented:
        mapped_campaign_id = campaign_map.get(src.campaign_id)
        if not mapped_campaign_id:
            continue
        db.add(_clone_row(MetricSegmented, src, overrides={"campaign_id": mapped_campaign_id}))
        cloned_metric_segmented += 1
    counts["cloned_metric_segmented"] = cloned_metric_segmented

    source_search_terms = (
        db.query(SearchTerm)
        .filter(
            SearchTerm.campaign_id.in_(
                db.query(Campaign.id).filter(Campaign.client_id == source_client.id)
            )
        )
        .all()
    )
    cloned_search_terms = 0
    for src in source_search_terms:
        mapped_campaign_id = campaign_map.get(src.campaign_id) if src.campaign_id else None
        mapped_ad_group_id = ad_group_map.get(src.ad_group_id) if src.ad_group_id else None
        if src.campaign_id and not mapped_campaign_id:
            continue
        db.add(
            _clone_row(
                SearchTerm,
                src,
                overrides={
                    "campaign_id": mapped_campaign_id,
                    "ad_group_id": mapped_ad_group_id,
                },
            )
        )
        cloned_search_terms += 1
    counts["cloned_search_terms"] = cloned_search_terms

    source_alerts = db.query(Alert).filter(Alert.client_id == source_client.id).all()
    for src in source_alerts:
        mapped_campaign_id = campaign_map.get(src.campaign_id) if src.campaign_id else None
        db.add(
            _clone_row(
                Alert,
                src,
                overrides={"client_id": target_client.id, "campaign_id": mapped_campaign_id},
            )
        )
    counts["cloned_alerts"] = len(source_alerts)

    source_recommendations = db.query(Recommendation).filter(Recommendation.client_id == source_client.id).all()
    for src in source_recommendations:
        mapped_campaign_id = campaign_map.get(src.campaign_id) if src.campaign_id else None
        mapped_ad_group_id = ad_group_map.get(src.ad_group_id) if src.ad_group_id else None
        db.add(
            _clone_row(
                Recommendation,
                src,
                overrides={
                    "client_id": target_client.id,
                    "campaign_id": mapped_campaign_id,
                    "ad_group_id": mapped_ad_group_id,
                },
            )
        )
    counts["cloned_recommendations"] = len(source_recommendations)

    source_negative_keywords = db.query(NegativeKeyword).filter(NegativeKeyword.client_id == source_client.id).all()
    for src in source_negative_keywords:
        mapped_campaign_id = campaign_map.get(src.campaign_id) if src.campaign_id else None
        mapped_ad_group_id = ad_group_map.get(src.ad_group_id) if src.ad_group_id else None
        db.add(
            _clone_row(
                NegativeKeyword,
                src,
                overrides={
                    "client_id": target_client.id,
                    "campaign_id": mapped_campaign_id,
                    "ad_group_id": mapped_ad_group_id,
                },
            )
        )
    counts["cloned_negative_keywords"] = len(source_negative_keywords)

    source_action_logs = db.query(ActionLog).filter(ActionLog.client_id == source_client.id).all()
    for src in source_action_logs:
        cloned_action = _clone_row(ActionLog, src, overrides={"client_id": target_client.id})
        db.add(cloned_action)
        db.flush()
        action_log_map[src.id] = cloned_action.id
    counts["cloned_action_logs"] = len(action_log_map)

    source_change_events = db.query(ChangeEvent).filter(ChangeEvent.client_id == source_client.id).all()
    for src in source_change_events:
        # resource_name is globally unique in change_events; cloned rows need a unique suffix.
        cloned_resource_name = f"{src.resource_name}::clone:{target_client.id}"
        db.add(
            _clone_row(
                ChangeEvent,
                src,
                overrides={
                    "client_id": target_client.id,
                    "resource_name": cloned_resource_name,
                    "action_log_id": action_log_map.get(src.action_log_id) if src.action_log_id else None,
                },
            )
        )
    counts["cloned_change_events"] = len(source_change_events)

    source_sync_logs = db.query(SyncLog).filter(SyncLog.client_id == source_client.id).all()
    for src in source_sync_logs:
        db.add(_clone_row(SyncLog, src, overrides={"client_id": target_client.id}))
    counts["cloned_sync_logs"] = len(source_sync_logs)

    return counts


def _sqlite_path_from_database_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None

    path_part = database_url.removeprefix("sqlite:///")
    if path_part in {"", ":memory:"}:
        return None

    return Path(path_part)


def _legacy_sqlite_path() -> Path | None:
    runtime_path = _sqlite_path_from_database_url(settings.database_url)
    if runtime_path is None:
        return None
    return settings.backend_dir / "data" / runtime_path.name


def _has_sqlite_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _fetchall_sqlite(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def _fetch_rows_with_in(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    ids: list[int],
) -> list[dict]:
    if not ids or not _has_sqlite_table(conn, table):
        return []
    placeholders = ", ".join("?" for _ in ids)
    query = f"SELECT * FROM {table} WHERE {column} IN ({placeholders})"
    return _fetchall_sqlite(conn, query, tuple(ids))


def _insert_sqlite_row(
    conn: sqlite3.Connection,
    table: str,
    payload: dict,
    table_columns_cache: dict[str, set[str]],
) -> int:
    if table not in table_columns_cache:
        table_columns_cache[table] = {
            row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }

    allowed_columns = table_columns_cache[table]
    filtered = {
        key: value
        for key, value in payload.items()
        if key != "id" and key in allowed_columns
    }
    if not filtered:
        raise RuntimeError(f"Brak danych do insertu dla tabeli '{table}'.")

    columns = list(filtered.keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    values = [filtered[column] for column in columns]
    cursor = conn.execute(sql, values)
    return int(cursor.lastrowid)


def _find_legacy_source_client(
    legacy_conn: sqlite3.Connection,
    target_client: Client,
    source_client_id: int | None = None,
) -> dict | None:
    if source_client_id is not None:
        row = legacy_conn.execute(
            "SELECT id, name, google_customer_id FROM clients WHERE id = ?",
            (source_client_id,),
        ).fetchone()
        return dict(row) if row else None

    normalized_target_cid = google_ads_service.normalize_customer_id(target_client.google_customer_id)
    if normalized_target_cid:
        row = legacy_conn.execute(
            """
            SELECT id, name, google_customer_id
            FROM clients
            WHERE REPLACE(google_customer_id, '-', '') = ?
            ORDER BY id
            LIMIT 1
            """,
            (normalized_target_cid,),
        ).fetchone()
        if row:
            return dict(row)

    row = legacy_conn.execute(
        """
        SELECT id, name, google_customer_id
        FROM clients
        WHERE LOWER(name) LIKE '%demo%'
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def _restore_runtime_from_legacy_sqlite(
    legacy_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_client_id: int,
    target_client_id: int,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    table_columns_cache: dict[str, set[str]] = {}

    campaign_map: dict[int, int] = {}
    ad_group_map: dict[int, int] = {}
    keyword_map: dict[int, int] = {}

    source_campaign_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM campaigns WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "campaigns") else []
    for row in source_campaign_rows:
        source_id = int(row.pop("id"))
        row["client_id"] = target_client_id
        campaign_map[source_id] = _insert_sqlite_row(target_conn, "campaigns", row, table_columns_cache)
    counts["restored_campaigns"] = len(campaign_map)

    source_campaign_ids = list(campaign_map.keys())
    source_ad_group_rows = _fetch_rows_with_in(legacy_conn, "ad_groups", "campaign_id", source_campaign_ids)
    for row in source_ad_group_rows:
        source_id = int(row.pop("id"))
        mapped_campaign_id = campaign_map.get(int(row.get("campaign_id") or 0))
        if not mapped_campaign_id:
            continue
        row["campaign_id"] = mapped_campaign_id
        ad_group_map[source_id] = _insert_sqlite_row(target_conn, "ad_groups", row, table_columns_cache)
    counts["restored_ad_groups"] = len(ad_group_map)

    source_ad_group_ids = list(ad_group_map.keys())
    source_keyword_rows = _fetch_rows_with_in(legacy_conn, "keywords", "ad_group_id", source_ad_group_ids)
    for row in source_keyword_rows:
        source_id = int(row.pop("id"))
        mapped_ad_group_id = ad_group_map.get(int(row.get("ad_group_id") or 0))
        if not mapped_ad_group_id:
            continue
        row["ad_group_id"] = mapped_ad_group_id
        keyword_map[source_id] = _insert_sqlite_row(target_conn, "keywords", row, table_columns_cache)
    counts["restored_keywords"] = len(keyword_map)

    source_keyword_ids = list(keyword_map.keys())
    source_keyword_daily_rows = _fetch_rows_with_in(legacy_conn, "keyword_daily", "keyword_id", source_keyword_ids)
    restored_keyword_daily = 0
    for row in source_keyword_daily_rows:
        row.pop("id", None)
        mapped_keyword_id = keyword_map.get(int(row.get("keyword_id") or 0))
        if not mapped_keyword_id:
            continue
        row["keyword_id"] = mapped_keyword_id
        _insert_sqlite_row(target_conn, "keyword_daily", row, table_columns_cache)
        restored_keyword_daily += 1
    counts["restored_keyword_daily"] = restored_keyword_daily

    source_metric_daily_rows = _fetch_rows_with_in(legacy_conn, "metrics_daily", "campaign_id", source_campaign_ids)
    restored_metric_daily = 0
    for row in source_metric_daily_rows:
        row.pop("id", None)
        mapped_campaign_id = campaign_map.get(int(row.get("campaign_id") or 0))
        if not mapped_campaign_id:
            continue
        row["campaign_id"] = mapped_campaign_id
        _insert_sqlite_row(target_conn, "metrics_daily", row, table_columns_cache)
        restored_metric_daily += 1
    counts["restored_metric_daily"] = restored_metric_daily

    source_metric_segmented_rows = _fetch_rows_with_in(
        legacy_conn,
        "metrics_segmented",
        "campaign_id",
        source_campaign_ids,
    )
    restored_metric_segmented = 0
    for row in source_metric_segmented_rows:
        row.pop("id", None)
        mapped_campaign_id = campaign_map.get(int(row.get("campaign_id") or 0))
        if not mapped_campaign_id:
            continue
        row["campaign_id"] = mapped_campaign_id
        _insert_sqlite_row(target_conn, "metrics_segmented", row, table_columns_cache)
        restored_metric_segmented += 1
    counts["restored_metric_segmented"] = restored_metric_segmented

    source_search_term_rows: list[dict] = []
    if _has_sqlite_table(legacy_conn, "search_terms"):
        conditions: list[str] = []
        params: list[int] = []
        if source_campaign_ids:
            placeholders = ", ".join("?" for _ in source_campaign_ids)
            conditions.append(f"campaign_id IN ({placeholders})")
            params.extend(source_campaign_ids)
        if source_ad_group_ids:
            placeholders = ", ".join("?" for _ in source_ad_group_ids)
            conditions.append(f"ad_group_id IN ({placeholders})")
            params.extend(source_ad_group_ids)
        if conditions:
            source_search_term_rows = _fetchall_sqlite(
                legacy_conn,
                f"SELECT * FROM search_terms WHERE {' OR '.join(conditions)}",
                tuple(params),
            )

    restored_search_terms = 0
    for row in source_search_term_rows:
        row.pop("id", None)
        raw_campaign_id = row.get("campaign_id")
        raw_ad_group_id = row.get("ad_group_id")
        mapped_campaign_id = campaign_map.get(int(raw_campaign_id or 0)) if raw_campaign_id else None
        mapped_ad_group_id = ad_group_map.get(int(raw_ad_group_id or 0)) if raw_ad_group_id else None
        if raw_campaign_id and not mapped_campaign_id:
            continue
        row["campaign_id"] = mapped_campaign_id
        row["ad_group_id"] = mapped_ad_group_id
        _insert_sqlite_row(target_conn, "search_terms", row, table_columns_cache)
        restored_search_terms += 1
    counts["restored_search_terms"] = restored_search_terms

    source_recommendation_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM recommendations WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "recommendations") else []
    restored_recommendations = 0
    for row in source_recommendation_rows:
        row.pop("id", None)
        row["client_id"] = target_client_id
        if row.get("campaign_id"):
            row["campaign_id"] = campaign_map.get(int(row["campaign_id"]))
        if row.get("ad_group_id"):
            row["ad_group_id"] = ad_group_map.get(int(row["ad_group_id"]))
        _insert_sqlite_row(target_conn, "recommendations", row, table_columns_cache)
        restored_recommendations += 1
    counts["restored_recommendations"] = restored_recommendations

    source_negative_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM negative_keywords WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "negative_keywords") else []
    restored_negative = 0
    for row in source_negative_rows:
        row.pop("id", None)
        row["client_id"] = target_client_id
        if row.get("campaign_id"):
            row["campaign_id"] = campaign_map.get(int(row["campaign_id"]))
        if row.get("ad_group_id"):
            row["ad_group_id"] = ad_group_map.get(int(row["ad_group_id"]))
        _insert_sqlite_row(target_conn, "negative_keywords", row, table_columns_cache)
        restored_negative += 1
    counts["restored_negative_keywords"] = restored_negative

    source_alert_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM alerts WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "alerts") else []
    restored_alerts = 0
    for row in source_alert_rows:
        row.pop("id", None)
        row["client_id"] = target_client_id
        if row.get("campaign_id"):
            row["campaign_id"] = campaign_map.get(int(row["campaign_id"]))
        _insert_sqlite_row(target_conn, "alerts", row, table_columns_cache)
        restored_alerts += 1
    counts["restored_alerts"] = restored_alerts

    source_sync_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM sync_logs WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "sync_logs") else []
    restored_sync_logs = 0
    for row in source_sync_rows:
        row.pop("id", None)
        row["client_id"] = target_client_id
        _insert_sqlite_row(target_conn, "sync_logs", row, table_columns_cache)
        restored_sync_logs += 1
    counts["restored_sync_logs"] = restored_sync_logs

    source_change_rows = _fetchall_sqlite(
        legacy_conn,
        "SELECT * FROM change_events WHERE client_id = ?",
        (source_client_id,),
    ) if _has_sqlite_table(legacy_conn, "change_events") else []
    restored_change_events = 0
    for row in source_change_rows:
        source_event_id = int(row.pop("id"))
        base_resource_name = row.get("resource_name") or f"legacy-change-event-{source_event_id}"
        row["client_id"] = target_client_id
        row["action_log_id"] = None
        row["resource_name"] = f"{base_resource_name}::legacy:{target_client_id}:{source_event_id}"
        _insert_sqlite_row(target_conn, "change_events", row, table_columns_cache)
        restored_change_events += 1
    counts["restored_change_events"] = restored_change_events

    return counts


@router.post("/discover")
def discover_clients(
    customer_ids: str = Query(None, description="Opcjonalne: numery kont Google Ads po przecinku (np. 123-456-7890)"),
    db: Session = Depends(get_db),
):
    """Auto-discover client accounts from Google Ads MCC and add them to DB."""
    _ensure_discover_ready()

    try:
        accounts = google_ads_service.discover_accounts()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not accounts:
        return {
            "message": "Nie znaleziono kont klienckich w MCC.",
            "added": 0,
            "skipped": 0,
        }

    if customer_ids:
        requested = {
            cid.replace("-", "").strip() for cid in customer_ids.split(",") if cid.strip()
        }
        accounts = [
            account
            for account in accounts
            if account["customer_id"].replace("-", "") in requested
        ]
        if not accounts:
            return {
                "message": "Nie znaleziono podanych kont w MCC.",
                "added": 0,
                "skipped": 0,
            }

    added = 0
    skipped = 0
    for account in accounts:
        existing = db.query(Client).filter(
            Client.google_customer_id == account["customer_id"]
        ).first()
        if existing:
            skipped += 1
            continue

        db.add(Client(name=account["name"], google_customer_id=account["customer_id"]))
        added += 1

    db.commit()
    logger.info(f"Discover: added={added}, skipped={skipped}")
    return {
        "message": f"Dodano {added} klientow ({skipped} juz istnialo).",
        "added": added,
        "skipped": skipped,
    }


@router.get("/", response_model=PaginatedResponse)
def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    """List all clients with pagination and optional search."""
    query = db.query(Client)
    if search:
        query = query.filter(Client.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a single client by ID."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/", response_model=ClientResponse, status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client."""
    existing = db.query(Client).filter(Client.google_customer_id == data.google_customer_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Client with this Google Customer ID already exists")

    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    data: ClientUpdate,
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Partially update a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Edycja klienta",
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client


@router.post("/{client_id}/hard-reset")
def hard_reset_client_data(
    client_id: int,
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Delete local runtime data for a client while keeping the client profile."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Twardy reset danych",
    )

    try:
        counts = _hard_reset_client_runtime_data(db, client)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Hard reset failed for client_id={}", client_id)
        raise HTTPException(status_code=500, detail="Nie udalo sie zresetowac danych klienta.") from exc

    logger.warning("Hard reset completed for client_id={} ({})", client.id, client.name)
    return {
        "success": True,
        "message": f"Dane lokalne klienta '{client.name}' zostaly wyczyszczone.",
        **counts,
    }


@router.post("/{client_id}/seed-demo-showcase")
def seed_demo_showcase_data(
    client_id: int,
    days: int = Query(30, ge=14, le=90, description="How many recent days to seed"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Seed local showcase-only DEMO data (ads, keyword daily, action log)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not is_demo_protected_client(db, client.id):
        raise HTTPException(
            status_code=400,
            detail="Endpoint seed-demo-showcase jest dostepny tylko dla klienta DEMO.",
        )

    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Seed danych demo showcase",
    )

    try:
        counts = _seed_demo_showcase_data(db, client=client, days=days)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Seed demo showcase failed for client_id={}", client_id)
        raise HTTPException(status_code=500, detail="Nie udalo sie wygenerowac danych demo showcase.") from exc

    return {
        "success": True,
        "message": f"Wygenerowano dane demo showcase dla klienta '{client.name}'.",
        "client_id": client.id,
        **counts,
    }


@router.post("/{client_id}/clone-runtime")
def clone_runtime_data_from_client(
    client_id: int,
    source_client_id: int = Query(..., description="Source client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Clone local runtime data from source client to target client."""
    target_client = db.query(Client).filter(Client.id == client_id).first()
    if not target_client:
        raise HTTPException(status_code=404, detail="Target client not found")
    ensure_demo_write_allowed(
        db,
        target_client.id,
        allow_demo_write=allow_demo_write,
        operation="Klonowanie danych runtime",
    )

    source_client = db.query(Client).filter(Client.id == source_client_id).first()
    if not source_client:
        raise HTTPException(status_code=404, detail="Source client not found")

    if source_client.id == target_client.id:
        raise HTTPException(status_code=400, detail="Source and target clients must be different")

    try:
        counts = _clone_runtime_data_between_clients(db, source_client, target_client)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Clone runtime data failed: source_client_id={} target_client_id={}",
            source_client.id,
            target_client.id,
        )
        raise HTTPException(status_code=500, detail="Nie udalo sie skopiowac danych runtime.") from exc

    return {
        "success": True,
        "message": (
            f"Skopiowano dane runtime z klienta '{source_client.name}' "
            f"do klienta '{target_client.name}'."
        ),
        "source_client_id": source_client.id,
        "target_client_id": target_client.id,
        **counts,
    }


@router.post("/{client_id}/restore-runtime-from-legacy")
def restore_runtime_from_legacy(
    client_id: int,
    source_client_id: int | None = Query(
        None,
        description="Optional legacy DB client ID override",
    ),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Restore client runtime data from legacy SQLite file (backend/data)."""
    target_client = db.query(Client).filter(Client.id == client_id).first()
    if not target_client:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db,
        target_client.id,
        allow_demo_write=allow_demo_write,
        operation="Odtwarzanie danych runtime z legacy",
    )

    runtime_path = _sqlite_path_from_database_url(settings.database_url)
    legacy_path = _legacy_sqlite_path()
    if runtime_path is None or legacy_path is None:
        raise HTTPException(status_code=500, detail="Aktualna konfiguracja nie uzywa SQLite.")
    if runtime_path.resolve() == legacy_path.resolve():
        raise HTTPException(status_code=400, detail="Legacy i runtime wskazuja ten sam plik bazy.")
    if not legacy_path.exists():
        raise HTTPException(status_code=404, detail=f"Brak legacy bazy: {legacy_path}")

    try:
        with sqlite3.connect(str(legacy_path)) as legacy_conn:
            legacy_conn.row_factory = sqlite3.Row
            source_client = _find_legacy_source_client(
                legacy_conn,
                target_client=target_client,
                source_client_id=source_client_id,
            )
            if not source_client:
                raise HTTPException(
                    status_code=404,
                    detail="Nie znaleziono pasujacego klienta w legacy bazie.",
                )

            reset_counts = _hard_reset_client_runtime_data(db, target_client)
            db.commit()

            with sqlite3.connect(str(runtime_path)) as target_conn:
                target_conn.row_factory = sqlite3.Row
                target_conn.execute("PRAGMA foreign_keys = ON")
                target_conn.execute("PRAGMA journal_mode = WAL")
                with target_conn:
                    restore_counts = _restore_runtime_from_legacy_sqlite(
                        legacy_conn=legacy_conn,
                        target_conn=target_conn,
                        source_client_id=int(source_client["id"]),
                        target_client_id=target_client.id,
                    )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Legacy restore failed for target_client_id={} from legacy_path={}",
            target_client.id,
            legacy_path,
        )
        raise HTTPException(status_code=500, detail="Nie udalo sie odtworzyc danych z legacy bazy.") from exc

    return {
        "success": True,
        "message": (
            f"Odtworzono dane runtime klienta '{target_client.name}' "
            f"z legacy klienta '{source_client['name']}'."
        ),
        "legacy_path": str(legacy_path),
        "runtime_path": str(runtime_path),
        "target_client_id": target_client.id,
        "source_legacy_client_id": int(source_client["id"]),
        "source_legacy_customer_id": source_client["google_customer_id"],
        **reset_counts,
        **restore_counts,
    }


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Delete a client and all associated data (cascade)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Usuwanie klienta",
    )

    db.delete(client)
    db.commit()
    return {"message": f"Client '{client.name}' deleted", "success": True}
