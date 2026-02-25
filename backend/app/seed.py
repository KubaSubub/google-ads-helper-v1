"""
Seed the database with realistic demo data for development and testing.

Run with: python -m app.seed
"""

import random
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, init_db
from app.models import (
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily, MetricSegmented,
    ActionLog, ChangeEvent,
)


# Deterministic seed for reproducibility
RNG = random.Random(42)

# Polish cities for geo breakdown
GEO_CITIES = [
    "Warszawa", "Kraków", "Wrocław", "Poznań", "Gdańsk",
    "Łódź", "Katowice", "Lublin", "Szczecin", "Bydgoszcz",
]

DEVICES = ["MOBILE", "DESKTOP", "TABLET"]


def _rand_is(rng, low=0.10, high=0.95):
    """Generate a random impression share value (0.0-1.0)."""
    return round(rng.uniform(low, high), 4)


def _rand_qs_enum(rng):
    """Generate a random QS enum value: 1=BELOW_AVERAGE, 2=AVERAGE, 3=ABOVE_AVERAGE."""
    return rng.choices([1, 2, 3], weights=[20, 50, 30], k=1)[0]


def seed_demo_data():
    """Generate realistic demo data for the Google Ads Helper app."""
    init_db()
    db = SessionLocal()

    # Check if data already exists
    if db.query(Client).count() > 0:
        print("⚠️  Database already contains data. Skipping seed.")
        db.close()
        return

    print("🌱 Seeding demo data...")

    # -----------------------------------------------------------------------
    # Client
    # -----------------------------------------------------------------------
    client = Client(
        name="Demo Meble Sp. z o.o.",
        google_customer_id="123-456-7890",
        industry="E-commerce - Meble",
        website="https://demo-meble.pl",
        target_audience="Młode małżeństwa, 25-40 lat, zainteresowani wyposażeniem domu",
        usp="Darmowa dostawa, montaż gratis, 30-dniowy zwrot",
        competitors=["meble-x.pl", "furni-store.com", "domowy-sklep.pl"],
        seasonality=[
            {"period": "Black Friday", "multiplier": 2.5},
            {"period": "Q1", "multiplier": 0.7},
            {"period": "Wakacje", "multiplier": 0.8},
        ],
        business_rules={
            "min_roas": 3.0,
            "max_daily_budget": 500,
            "excluded_geos": ["ZA", "IN"],
        },
        notes="Kluczowy klient. Fokus na branded search i kanapa/łóżka. Sezon wysoki: wrzesień-grudzień.",
    )
    db.add(client)
    db.flush()

    # -----------------------------------------------------------------------
    # Campaigns (with impression share + top impression %)
    # -----------------------------------------------------------------------
    campaigns_data = [
        ("Branded Search", "SEARCH", 150, "ENABLED"),
        ("Łóżka - Generic", "SEARCH", 300, "ENABLED"),
        ("Kanapy - Generic", "SEARCH", 250, "ENABLED"),
        ("Meble Biurowe", "SEARCH", 100, "ENABLED"),
        ("Shopping - Łóżka", "SHOPPING", 200, "ENABLED"),
        ("Display - Remarketing", "DISPLAY", 80, "PAUSED"),
    ]

    campaigns = []
    for i, (name, ctype, budget, status) in enumerate(campaigns_data, start=1):
        is_search = ctype == "SEARCH"
        c = Campaign(
            client_id=client.id,
            google_campaign_id=str(1000 + i),
            name=name,
            status=status,
            campaign_type=ctype,
            budget_micros=int(budget * 1_000_000),
            budget_type="DAILY",
            bidding_strategy="TARGET_CPA" if is_search else "TARGET_ROAS",
            start_date=date(2025, 1, 1),
            # Impression share (only for SEARCH)
            search_impression_share=_rand_is(RNG, 0.30, 0.85) if is_search else None,
            search_top_impression_share=_rand_is(RNG, 0.20, 0.70) if is_search else None,
            search_abs_top_impression_share=_rand_is(RNG, 0.10, 0.50) if is_search else None,
            search_budget_lost_is=_rand_is(RNG, 0.01, 0.15) if is_search else None,
            search_budget_lost_top_is=_rand_is(RNG, 0.02, 0.20) if is_search else None,
            search_budget_lost_abs_top_is=_rand_is(RNG, 0.03, 0.25) if is_search else None,
            search_rank_lost_is=_rand_is(RNG, 0.05, 0.30) if is_search else None,
            search_rank_lost_top_is=_rand_is(RNG, 0.10, 0.40) if is_search else None,
            search_rank_lost_abs_top_is=_rand_is(RNG, 0.15, 0.50) if is_search else None,
            search_click_share=_rand_is(RNG, 0.20, 0.75) if is_search else None,
            search_exact_match_is=_rand_is(RNG, 0.40, 0.95) if is_search else None,
            abs_top_impression_pct=_rand_is(RNG, 0.10, 0.45) if is_search else None,
            top_impression_pct=_rand_is(RNG, 0.25, 0.70) if is_search else None,
        )
        db.add(c)
        campaigns.append(c)
    db.flush()

    # -----------------------------------------------------------------------
    # Ad Groups & Keywords per campaign (with IS, QS, extended conv)
    # -----------------------------------------------------------------------
    ad_groups_config = {
        "Branded Search": [
            ("Brand - Exact", [
                ("demo meble", "EXACT"),
                ("meble demo", "EXACT"),
                ("demo meble sklep", "PHRASE"),
            ]),
        ],
        "Łóżka - Generic": [
            ("Łóżka drewniane", [
                ("łóżko drewniane", "PHRASE"),
                ("łóżko sosnowe", "PHRASE"),
                ("łóżko drewniane 160x200", "EXACT"),
                ("łóżko do sypialni drewniane", "BROAD"),
            ]),
            ("Łóżka tapicerowane", [
                ("łóżko tapicerowane", "PHRASE"),
                ("łóżko z zagłówkiem", "PHRASE"),
                ("łóżko tapicerowane 180x200", "EXACT"),
            ]),
        ],
        "Kanapy - Generic": [
            ("Kanapy narożne", [
                ("kanapa narożna", "PHRASE"),
                ("narożnik do salonu", "PHRASE"),
                ("sofa narożna rozkładana", "BROAD"),
            ]),
            ("Sofy", [
                ("sofa 3-osobowa", "PHRASE"),
                ("sofa do salonu", "BROAD"),
                ("sofa rozkładana", "PHRASE"),
            ]),
        ],
        "Meble Biurowe": [
            ("Biurka", [
                ("biurko do domu", "PHRASE"),
                ("biurko gamingowe", "BROAD"),
                ("biurko regulowane", "PHRASE"),
            ]),
        ],
    }

    all_ad_groups = []
    all_keywords = []
    for campaign in campaigns:
        ag_configs = ad_groups_config.get(campaign.name, [])
        for j, (ag_name, keywords_list) in enumerate(ag_configs, start=1):
            ag = AdGroup(
                campaign_id=campaign.id,
                google_ad_group_id=str(2000 + campaign.id * 10 + j),
                name=ag_name,
                status="ENABLED",
                bid_micros=int(RNG.uniform(1.0, 5.0) * 1_000_000),
            )
            db.add(ag)
            db.flush()
            all_ad_groups.append(ag)

            for kw_text, match in keywords_list:
                clicks = RNG.randint(10, 500)
                impressions = RNG.randint(200, 10000)
                cost = RNG.uniform(20, 800)
                conversions = round(RNG.uniform(0, 30), 2)
                conv_value = round(conversions * RNG.uniform(100, 250), 2)
                cpa = round(cost / conversions, 2) if conversions > 0 else 0
                qs = RNG.choices(range(1, 11), weights=[2, 3, 5, 8, 12, 15, 18, 20, 12, 5], k=1)[0]

                kw = Keyword(
                    ad_group_id=ag.id,
                    google_keyword_id=str(RNG.randint(30000, 99999)),
                    text=kw_text,
                    match_type=match,
                    status="ENABLED",
                    clicks=clicks,
                    impressions=impressions,
                    cost_micros=int(cost * 1_000_000),
                    conversions=conversions,
                    conversion_value_micros=int(conv_value * 1_000_000),
                    ctr=int(RNG.uniform(1.0, 8.0) * 10_000),
                    avg_cpc_micros=int(RNG.uniform(0.5, 5.0) * 1_000_000),
                    cpa_micros=int(cpa * 1_000_000),
                    quality_score=qs,
                    # Impression share (rank-based only for keywords)
                    search_impression_share=_rand_is(RNG, 0.20, 0.90),
                    search_top_impression_share=_rand_is(RNG, 0.15, 0.70),
                    search_abs_top_impression_share=_rand_is(RNG, 0.05, 0.45),
                    search_rank_lost_is=_rand_is(RNG, 0.05, 0.35),
                    search_rank_lost_top_is=_rand_is(RNG, 0.10, 0.45),
                    search_rank_lost_abs_top_is=_rand_is(RNG, 0.15, 0.55),
                    search_exact_match_is=_rand_is(RNG, 0.30, 0.95),
                    # Historical QS components
                    historical_quality_score=qs,
                    historical_creative_quality=_rand_qs_enum(RNG),
                    historical_landing_page_quality=_rand_qs_enum(RNG),
                    historical_search_predicted_ctr=_rand_qs_enum(RNG),
                    # Extended conversions
                    all_conversions=round(conversions * RNG.uniform(1.0, 1.3), 2),
                    all_conversions_value_micros=int(conv_value * RNG.uniform(1.0, 1.3) * 1_000_000),
                    cross_device_conversions=round(conversions * RNG.uniform(0.05, 0.25), 2),
                    value_per_conversion_micros=int((conv_value / conversions) * 1_000_000) if conversions > 0 else 0,
                    conversions_value_per_cost=round(conv_value / cost, 2) if cost > 0 else 0,
                    # Top impression %
                    abs_top_impression_pct=round(RNG.uniform(0.05, 0.40), 4),
                    top_impression_pct=round(RNG.uniform(0.15, 0.65), 4),
                )
                db.add(kw)
                all_keywords.append(kw)

    db.flush()

    # -----------------------------------------------------------------------
    # Search Terms (with extended conversions)
    # -----------------------------------------------------------------------
    search_terms_pool = [
        "łóżko drewniane do sypialni", "łóżko sosnowe 160x200 cena",
        "tanie łóżko drewniane", "łóżko drewniane sklep internetowy",
        "łóżko z szufladami drewniane", "łóżko drewniane białe",
        "kanapa narożna do salonu", "narożnik rozkładany z funkcją spania",
        "sofa narożna szara", "kanapa narożna tania", "narożnik prawy",
        "sofa 3 osobowa do salonu", "sofa rozkładana codziennego spania",
        "biurko do pracy zdalnej", "biurko gamingowe led",
        "biurko regulowane elektrycznie cena",
        "demo meble opinie", "demo meble sklep", "meble demo pl",
        "łóżko tapicerowane szare 180x200", "łóżko kontynentalne",
        "jak wybrać łóżko do sypialni",  # Informational
        "ikea łóżko malm",  # Competitor brand
        "materac do łóżka",  # Loosely related
    ]

    for ag in all_ad_groups:
        terms = RNG.sample(search_terms_pool, min(len(search_terms_pool), RNG.randint(5, 12)))
        for term_text in terms:
            clicks = RNG.randint(1, 150)
            impressions = RNG.randint(clicks * 5, clicks * 30)
            cost = clicks * RNG.uniform(0.5, 4.0)
            conversions = round(RNG.uniform(0, clicks * 0.1), 2)
            conv_value = round(conversions * RNG.uniform(80, 200), 2)

            campaign = db.get(Campaign, ag.campaign_id)
            campaign_name = campaign.name if campaign else ""
            keywords_for_campaign = ad_groups_config.get(campaign_name, [])
            if keywords_for_campaign:
                keyword_text = RNG.choice([kw for kw, _ in keywords_for_campaign[0][1]])
            else:
                keyword_text = "generic keyword"

            st = SearchTerm(
                ad_group_id=ag.id,
                text=term_text,
                keyword_text=keyword_text,
                clicks=clicks,
                impressions=impressions,
                cost_micros=int(cost * 1_000_000),
                conversions=conversions,
                conversion_value_micros=int(conv_value * 1_000_000),
                ctr=int((clicks / impressions * 100) * 10_000 if impressions else 0),
                conversion_rate=int((conversions / clicks * 100) * 10_000 if clicks else 0),
                date_from=date.today() - timedelta(days=30),
                date_to=date.today(),
                # Extended conversions
                all_conversions=round(conversions * RNG.uniform(1.0, 1.2), 2) if conversions > 0 else None,
                all_conversions_value_micros=int(conv_value * RNG.uniform(1.0, 1.2) * 1_000_000) if conv_value > 0 else None,
                cross_device_conversions=round(conversions * RNG.uniform(0.03, 0.15), 2) if conversions > 0 else None,
                value_per_conversion_micros=int((conv_value / conversions) * 1_000_000) if conversions > 0 else None,
                conversions_value_per_cost=round(conv_value / cost, 2) if cost > 0 else None,
            )
            db.add(st)

    # -----------------------------------------------------------------------
    # Ads (RSA)
    # -----------------------------------------------------------------------
    for ag in all_ad_groups:
        for ad_idx in range(RNG.randint(1, 3)):
            clicks = RNG.randint(50, 1000)
            impressions = RNG.randint(clicks * 8, clicks * 25)
            cost = clicks * RNG.uniform(0.8, 3.5)
            conversions = int(RNG.uniform(0, clicks * 0.08))

            ad = Ad(
                ad_group_id=ag.id,
                google_ad_id=str(RNG.randint(50000, 99999)),
                ad_type="RESPONSIVE_SEARCH_AD",
                status="ENABLED",
                final_url="https://demo-meble.pl/produkty",
                headlines=[
                    {"text": "Demo Meble - Darmowa Dostawa", "pinned_position": None},
                    {"text": "Łóżka od 999 zł", "pinned_position": 1},
                    {"text": "Montaż Gratis", "pinned_position": None},
                    {"text": "30 Dni na Zwrot", "pinned_position": None},
                ],
                descriptions=[
                    {"text": "Sprawdź naszą ofertę łóżek i kanap. Darmowa dostawa i montaż w cenie!"},
                    {"text": "Ponad 500 modeli mebli. Sklep internetowy z darmowym zwrotem do 30 dni."},
                ],
                clicks=clicks,
                impressions=impressions,
                cost_micros=int(cost * 1_000_000),
                conversions=conversions,
                ctr=int((clicks / impressions * 100) * 10_000),
            )
            db.add(ad)

    # -----------------------------------------------------------------------
    # Daily Metrics (last 90 days, with IS + extended conv + top impression)
    # -----------------------------------------------------------------------
    for campaign in campaigns:
        if campaign.status == "PAUSED":
            continue

        base_clicks = RNG.randint(30, 200)
        base_cost = round(base_clicks * RNG.uniform(1.0, 3.0), 2)
        is_search = campaign.campaign_type == "SEARCH"

        for day_offset in range(90):
            d = date.today() - timedelta(days=day_offset)
            trend_factor = 1 + (90 - day_offset) * 0.002
            day_of_week_factor = 0.7 if d.weekday() >= 5 else 1.0

            clicks = max(1, int(base_clicks * trend_factor * day_of_week_factor * RNG.uniform(0.6, 1.4)))
            impressions = int(clicks * RNG.uniform(10, 25))
            cost_usd = round(clicks * RNG.uniform(0.8, 3.5) * day_of_week_factor, 2)
            conversions = round(max(0.0, clicks * RNG.uniform(0.01, 0.08)), 2)
            conv_value = round(conversions * RNG.uniform(100, 250), 2)

            dm = MetricDaily(
                campaign_id=campaign.id,
                date=d,
                clicks=clicks,
                impressions=impressions,
                ctr=round(clicks / impressions * 100 if impressions else 0, 2),
                conversions=conversions,
                conversion_value_micros=int(conv_value * 1_000_000),
                conversion_rate=round(conversions / clicks * 100 if clicks else 0, 2),
                cost_micros=int(cost_usd * 1_000_000),
                roas=round(conv_value / cost_usd if cost_usd > 0 else 0, 2),
                avg_cpc_micros=int((cost_usd / clicks) * 1_000_000 if clicks else 0),
                # Impression share (daily, only for SEARCH)
                search_impression_share=_rand_is(RNG, 0.25, 0.85) if is_search else None,
                search_top_impression_share=_rand_is(RNG, 0.15, 0.65) if is_search else None,
                search_abs_top_impression_share=_rand_is(RNG, 0.05, 0.40) if is_search else None,
                search_budget_lost_is=_rand_is(RNG, 0.01, 0.12) if is_search else None,
                search_budget_lost_top_is=_rand_is(RNG, 0.02, 0.18) if is_search else None,
                search_budget_lost_abs_top_is=_rand_is(RNG, 0.03, 0.22) if is_search else None,
                search_rank_lost_is=_rand_is(RNG, 0.05, 0.25) if is_search else None,
                search_rank_lost_top_is=_rand_is(RNG, 0.08, 0.35) if is_search else None,
                search_rank_lost_abs_top_is=_rand_is(RNG, 0.12, 0.45) if is_search else None,
                search_click_share=_rand_is(RNG, 0.20, 0.70) if is_search else None,
                # Extended conversions
                all_conversions=round(conversions * RNG.uniform(1.0, 1.25), 2) if conversions > 0 else None,
                all_conversions_value_micros=int(conv_value * RNG.uniform(1.0, 1.25) * 1_000_000) if conv_value > 0 else None,
                cross_device_conversions=round(conversions * RNG.uniform(0.05, 0.20), 2) if conversions > 0 else None,
                value_per_conversion_micros=int((conv_value / conversions) * 1_000_000) if conversions > 0 else None,
                conversions_value_per_cost=round(conv_value / cost_usd, 2) if cost_usd > 0 else None,
                # Top impression %
                abs_top_impression_pct=round(RNG.uniform(0.05, 0.40), 4) if is_search else None,
                top_impression_pct=round(RNG.uniform(0.15, 0.65), 4) if is_search else None,
            )
            db.add(dm)

    # -----------------------------------------------------------------------
    # MetricSegmented — device breakdown (last 30 days, SEARCH campaigns only)
    # -----------------------------------------------------------------------
    search_campaigns = [c for c in campaigns if c.campaign_type == "SEARCH" and c.status == "ENABLED"]

    for campaign in search_campaigns:
        for day_offset in range(30):
            d = date.today() - timedelta(days=day_offset)
            day_of_week_factor = 0.7 if d.weekday() >= 5 else 1.0

            # Device distribution: mobile ~55%, desktop ~35%, tablet ~10%
            device_weights = {"MOBILE": 0.55, "DESKTOP": 0.35, "TABLET": 0.10}
            total_clicks = int(RNG.randint(30, 150) * day_of_week_factor)

            for device, weight in device_weights.items():
                dev_clicks = max(1, int(total_clicks * weight * RNG.uniform(0.7, 1.3)))
                dev_impressions = int(dev_clicks * RNG.uniform(10, 25))
                dev_cost = round(dev_clicks * RNG.uniform(0.8, 3.5), 2)
                dev_conv = round(max(0.0, dev_clicks * RNG.uniform(0.01, 0.06)), 2)
                dev_conv_value = round(dev_conv * RNG.uniform(100, 250), 2)

                ms = MetricSegmented(
                    campaign_id=campaign.id,
                    date=d,
                    device=device,
                    geo_city=None,
                    clicks=dev_clicks,
                    impressions=dev_impressions,
                    ctr=round(dev_clicks / dev_impressions * 100 if dev_impressions else 0, 2),
                    conversions=dev_conv,
                    conversion_value_micros=int(dev_conv_value * 1_000_000),
                    cost_micros=int(dev_cost * 1_000_000),
                    avg_cpc_micros=int((dev_cost / dev_clicks) * 1_000_000) if dev_clicks else 0,
                    search_impression_share=_rand_is(RNG, 0.20, 0.80),
                )
                db.add(ms)

    # -----------------------------------------------------------------------
    # MetricSegmented — geo breakdown (last 7 days, SEARCH campaigns only)
    # -----------------------------------------------------------------------
    for campaign in search_campaigns:
        for day_offset in range(7):
            d = date.today() - timedelta(days=day_offset)

            # Pick 4-6 random cities per day per campaign
            day_cities = RNG.sample(GEO_CITIES, RNG.randint(4, 6))
            for city in day_cities:
                geo_clicks = RNG.randint(3, 50)
                geo_impressions = int(geo_clicks * RNG.uniform(8, 20))
                geo_cost = round(geo_clicks * RNG.uniform(0.8, 3.0), 2)
                geo_conv = round(max(0.0, geo_clicks * RNG.uniform(0.01, 0.06)), 2)
                geo_conv_value = round(geo_conv * RNG.uniform(100, 250), 2)

                ms = MetricSegmented(
                    campaign_id=campaign.id,
                    date=d,
                    device=None,
                    geo_city=city,
                    clicks=geo_clicks,
                    impressions=geo_impressions,
                    ctr=round(geo_clicks / geo_impressions * 100 if geo_impressions else 0, 2),
                    conversions=geo_conv,
                    conversion_value_micros=int(geo_conv_value * 1_000_000),
                    cost_micros=int(geo_cost * 1_000_000),
                    avg_cpc_micros=int((geo_cost / geo_clicks) * 1_000_000) if geo_clicks else 0,
                    search_impression_share=_rand_is(RNG, 0.15, 0.75),
                )
                db.add(ms)

    db.commit()

    # -----------------------------------------------------------------------
    # Action Log (Helper actions — for unified timeline demo)
    # -----------------------------------------------------------------------
    import json

    action_log_data = [
        {
            "client_id": client.id,
            "action_type": "PAUSE_KEYWORD",
            "entity_type": "keyword",
            "entity_id": str(all_keywords[0].id) if all_keywords else "1",
            "old_value_json": json.dumps({"status": "ENABLED", "bid_micros": 2500000}),
            "new_value_json": json.dumps({"status": "PAUSED"}),
            "status": "SUCCESS",
            "executed_at": datetime.utcnow() - timedelta(hours=3),
        },
        {
            "client_id": client.id,
            "action_type": "UPDATE_BID",
            "entity_type": "keyword",
            "entity_id": str(all_keywords[1].id) if len(all_keywords) > 1 else "2",
            "old_value_json": json.dumps({"bid_micros": 1500000}),
            "new_value_json": json.dumps({"bid_micros": 1800000}),
            "status": "SUCCESS",
            "executed_at": datetime.utcnow() - timedelta(hours=8),
        },
        {
            "client_id": client.id,
            "action_type": "ADD_NEGATIVE",
            "entity_type": "search_term",
            "entity_id": "999",
            "old_value_json": None,
            "new_value_json": json.dumps({"keyword_text": "meble za darmo", "match_type": "EXACT"}),
            "status": "SUCCESS",
            "executed_at": datetime.utcnow() - timedelta(days=1, hours=2),
        },
        {
            "client_id": client.id,
            "action_type": "INCREASE_BUDGET",
            "entity_type": "campaign",
            "entity_id": str(campaigns[0].id),
            "old_value_json": json.dumps({"budget_micros": 50000000}),
            "new_value_json": json.dumps({"budget_micros": 65000000}),
            "status": "SUCCESS",
            "executed_at": datetime.utcnow() - timedelta(days=2),
        },
        {
            "client_id": client.id,
            "action_type": "PAUSE_KEYWORD",
            "entity_type": "keyword",
            "entity_id": str(all_keywords[3].id) if len(all_keywords) > 3 else "4",
            "old_value_json": json.dumps({"status": "ENABLED"}),
            "new_value_json": json.dumps({"status": "PAUSED"}),
            "status": "REVERTED",
            "reverted_at": datetime.utcnow() - timedelta(days=3),
            "executed_at": datetime.utcnow() - timedelta(days=4),
        },
    ]

    all_action_logs = []
    for ald in action_log_data:
        al = ActionLog(**ald)
        db.add(al)
        all_action_logs.append(al)
    db.flush()

    # -----------------------------------------------------------------------
    # Change Events (external changes — from Google Ads UI / API / scripts)
    # -----------------------------------------------------------------------
    users = ["jan.kowalski@demo-meble.pl", "anna.nowak@demo-meble.pl", "api@agency.pl"]
    client_types = ["GOOGLE_ADS_WEB_CLIENT", "GOOGLE_ADS_WEB_CLIENT", "GOOGLE_ADS_API"]
    resource_types = [
        "CAMPAIGN", "AD_GROUP_CRITERION", "CAMPAIGN_BUDGET",
        "AD_GROUP", "AD_GROUP_AD", "CAMPAIGN_CRITERION",
    ]
    operations = ["UPDATE", "UPDATE", "UPDATE", "CREATE", "REMOVE"]
    camp_names_for_events = [c.name for c in campaigns[:3]]

    change_events_data = []
    for i in range(35):
        days_ago = RNG.randint(0, 29)
        hours_ago = RNG.randint(0, 23)
        minutes_ago = RNG.randint(0, 59)
        event_time = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        user_idx = RNG.randint(0, len(users) - 1)
        res_type = RNG.choice(resource_types)
        op = RNG.choice(operations)

        # Build realistic old/new JSON based on resource type and operation
        if res_type == "AD_GROUP_CRITERION" and op == "UPDATE":
            old_json = json.dumps({"cpc_bid_micros": str(RNG.randint(500000, 5000000)), "status": "ENABLED"})
            new_bid = RNG.randint(500000, 5000000)
            new_json = json.dumps({"cpc_bid_micros": str(new_bid), "status": "ENABLED"})
            changed = json.dumps(["cpc_bid_micros"])
            ent_name = RNG.choice(["kanapa narożna", "łóżko podwójne", "stół drewniany", "krzesło biurowe", "szafa przesuwna"])
        elif res_type == "CAMPAIGN_BUDGET" and op == "UPDATE":
            old_budget = RNG.randint(30000000, 100000000)
            new_budget = int(old_budget * RNG.uniform(0.8, 1.3))
            old_json = json.dumps({"amount_micros": str(old_budget)})
            new_json = json.dumps({"amount_micros": str(new_budget)})
            changed = json.dumps(["amount_micros"])
            ent_name = None
        elif res_type == "CAMPAIGN" and op == "UPDATE":
            statuses = ["ENABLED", "PAUSED"]
            old_status = RNG.choice(statuses)
            new_status = "PAUSED" if old_status == "ENABLED" else "ENABLED"
            old_json = json.dumps({"status": old_status})
            new_json = json.dumps({"status": new_status})
            changed = json.dumps(["status"])
            ent_name = RNG.choice(camp_names_for_events) if camp_names_for_events else None
        elif op == "CREATE":
            old_json = None
            new_json = json.dumps({"name": f"New element {i}", "status": "ENABLED"})
            changed = None
            ent_name = f"New element {i}"
        elif op == "REMOVE":
            old_json = json.dumps({"name": f"Removed element {i}", "status": "ENABLED"})
            new_json = None
            changed = None
            ent_name = f"Removed element {i}"
        else:
            old_json = json.dumps({"status": "ENABLED"})
            new_json = json.dumps({"status": "PAUSED"})
            changed = json.dumps(["status"])
            ent_name = None

        camp_id_str = str(campaigns[RNG.randint(0, min(2, len(campaigns) - 1))].google_campaign_id)
        entity_id_str = str(RNG.randint(100000, 999999))
        resource_name = f"customers/1234567890/changeEvents/{1000 + i}"
        change_resource_name = f"customers/1234567890/campaigns/{camp_id_str}/adGroupCriteria/{entity_id_str}"

        camp_name = None
        for c in campaigns:
            if str(c.google_campaign_id) == camp_id_str:
                camp_name = c.name
                break

        # Link a couple of events to action_log entries
        linked_action_id = None
        if i < len(all_action_logs) and RNG.random() < 0.3:
            linked_action_id = all_action_logs[i].id

        change_events_data.append(ChangeEvent(
            client_id=client.id,
            resource_name=resource_name,
            change_date_time=event_time,
            user_email=users[user_idx],
            client_type=client_types[user_idx],
            change_resource_type=res_type,
            change_resource_name=change_resource_name,
            resource_change_operation=op,
            changed_fields=changed,
            old_resource_json=old_json,
            new_resource_json=new_json,
            action_log_id=linked_action_id,
            entity_id=entity_id_str,
            entity_name=ent_name,
            campaign_name=camp_name,
        ))

    for ce in change_events_data:
        db.add(ce)

    db.commit()
    db.close()

    print("Done! Demo data seeded successfully!")
    print("   - 1 client (Demo Meble)")
    print(f"   - {len(campaigns)} campaigns (with IS + top impression %)")
    print(f"   - {len(all_ad_groups)} ad groups")
    print("   - Keywords (with IS, QS historical, extended conv, top impression %)")
    print("   - Search terms (with extended conversions)")
    print("   - 90 days of daily metrics (with IS, extended conv, top impression %)")
    print("   - 30 days of device breakdown (MetricSegmented)")
    print("   - 7 days of geo breakdown (MetricSegmented)")
    print(f"   - {len(all_action_logs)} action log entries")
    print(f"   - {len(change_events_data)} change events (external history)")


if __name__ == "__main__":
    seed_demo_data()
