"""
Seed the database with realistic demo data for development and testing.

Run with: python -m app.seed
"""

import random
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, init_db
from app.models import (
    Client, Campaign, AdGroup, Keyword, KeywordDaily, SearchTerm, Ad, MetricDaily, MetricSegmented,
    ActionLog, ChangeEvent, Alert, NegativeKeyword, ConversionAction,
)
from app.models.negative_keyword_list import NegativeKeywordList, NegativeKeywordListItem


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
    try:
        _seed_demo_data_impl(db)
    finally:
        db.close()


def _seed_demo_data_impl(db):

    # Check if data already exists
    if db.query(Client).count() > 0:
        print("[!] Database already contains data. Skipping seed.")
        return

    print("[*] Seeding demo data...")

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
    # GAP 1D: Smart Bidding targets per strategy
    # GAP 1A: primary_status + reasons
    # GAP 1C: one ECPC campaign for deprecation testing
    campaigns_data = [
        ("Branded Search", "SEARCH", 150, "ENABLED", "TARGET_CPA"),
        ("Łóżka - Generic", "SEARCH", 300, "ENABLED", "TARGET_ROAS"),
        ("Kanapy - Generic", "SEARCH", 250, "ENABLED", "TARGET_CPA"),
        ("Meble Biurowe", "SEARCH", 100, "ENABLED", "ENHANCED_CPC"),
        ("Shopping - Łóżka", "SHOPPING", 200, "ENABLED", "TARGET_ROAS"),
        ("Display - Remarketing", "DISPLAY", 80, "PAUSED", "MAXIMIZE_CONVERSIONS"),
        ("PMax - Meble Ogólne", "PERFORMANCE_MAX", 350, "ENABLED", "MAXIMIZE_CONVERSION_VALUE"),
        ("Kanapy - Retarget", "SEARCH", 120, "ENABLED", "TARGET_CPA"),  # portfolio member
    ]

    campaigns = []
    for i, (name, ctype, budget, status, bid_strat) in enumerate(campaigns_data, start=1):
        is_search = ctype == "SEARCH"

        # GAP 1D: targets
        tcpa = int(budget * 0.15 * 1_000_000) if bid_strat in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") else None
        troas = round(RNG.uniform(2.5, 5.0), 2) if bid_strat in ("TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE") else None

        # GAP 1A: learning status — make "Kanapy - Generic" stuck in learning
        p_status = "ELIGIBLE" if name != "Kanapy - Generic" else "ELIGIBLE"
        p_reasons = None
        if name == "Kanapy - Generic":
            import json as _json
            p_reasons = _json.dumps(["BIDDING_STRATEGY_LEARNING"])
            p_status = "LEARNING"

        # GAP 1E: portfolio strategy — last two TARGET_CPA campaigns share a portfolio
        portfolio_id = None
        portfolio_resource = None
        if name in ("Kanapy - Generic", "Kanapy - Retarget"):
            portfolio_id = "777"
            portfolio_resource = "customers/1234567890/biddingStrategies/777"

        c = Campaign(
            client_id=client.id,
            google_campaign_id=str(1000 + i),
            name=name,
            status=status,
            campaign_type=ctype,
            budget_micros=int(budget * 1_000_000),
            budget_type="DAILY",
            bidding_strategy=bid_strat,
            target_cpa_micros=tcpa,
            target_roas=troas,
            primary_status=p_status,
            primary_status_reasons=p_reasons,
            bidding_strategy_resource_name=portfolio_resource,
            portfolio_bid_strategy_id=portfolio_id,
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
        "Shopping - Łóżka": [
            ("Shopping - Łóżka AG", [
                ("łóżko sklep", "BROAD"),
                ("kup łóżko online", "BROAD"),
                ("łóżko cena", "PHRASE"),
                ("łóżko z materacem", "BROAD"),
            ]),
        ],
        "Display - Remarketing": [
            ("Remarketing - Ogólny", [
                ("meble retargeting", "BROAD"),
                ("remarketing sofa", "BROAD"),
                ("display meble", "BROAD"),
            ]),
        ],
        "Kanapy - Retarget": [
            ("Kanapy Retarget AG", [
                ("kanapa retarget", "BROAD"),
                ("sofa retargeting", "BROAD"),
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

            # Landing page URLs per campaign theme
            _url_map = {
                "Sofy": ["https://demo-meble.pl/sofy", "https://demo-meble.pl/sofy/narozne", "https://demo-meble.pl/promocje/sofy"],
                "Kanapy": ["https://demo-meble.pl/kanapy", "https://demo-meble.pl/kanapy/rozkladane"],
                "Łóżka": ["https://demo-meble.pl/lozka", "https://demo-meble.pl/lozka/drewniane", "https://demo-meble.pl/lozka/tapicerowane"],
                "Biurka": ["https://demo-meble.pl/biurka", "https://demo-meble.pl/biurka/gamingowe"],
                "Shopping": ["https://demo-meble.pl/sklep"],
                "Display": ["https://demo-meble.pl/"],
                "PMax": ["https://demo-meble.pl/"],
            }
            url_key = next((k for k in _url_map if k in campaign.name), "Sofy")
            urls = _url_map[url_key]

            for kw_text, match in keywords_list:
                clicks = RNG.randint(10, 500)
                impressions = RNG.randint(200, 10000)
                cost = RNG.uniform(20, 800)
                conversions = round(RNG.uniform(0, 30), 2)
                conv_value = round(conversions * RNG.uniform(100, 250), 2)
                cpa = round(cost / conversions, 2) if conversions > 0 else 0
                qs = RNG.choices(range(1, 11), weights=[2, 3, 5, 8, 12, 15, 18, 20, 12, 5], k=1)[0]

                # Serving status distribution: mostly ELIGIBLE, some issues
                serving_status = RNG.choices(
                    ["ELIGIBLE", "LOW_SEARCH_VOLUME", "BELOW_FIRST_PAGE_BID", "RARELY_SERVED"],
                    weights=[60, 15, 15, 10],
                    k=1,
                )[0]

                kw = Keyword(
                    ad_group_id=ag.id,
                    google_keyword_id=str(RNG.randint(30000, 99999)),
                    text=kw_text,
                    match_type=match,
                    status="ENABLED",
                    serving_status=serving_status,
                    final_url=RNG.choice(urls),
                    clicks=clicks,
                    impressions=impressions,
                    cost_micros=int(cost * 1_000_000),
                    conversions=conversions,
                    conversion_value_micros=int(conv_value * 1_000_000),
                    ctr=round(RNG.uniform(1.0, 8.0), 2),
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
    # Keyword Daily Metrics (90 days per keyword)
    # Mark ~3 keywords as "waste" (0 conversions but high clicks) for demo
    # -----------------------------------------------------------------------
    waste_kw_ids = set(kw.id for kw in all_keywords[:3])  # first 3 keywords = waste

    for kw in all_keywords:
        is_waste = kw.id in waste_kw_ids
        base_clicks = max(1, (kw.clicks or 10) // 90)
        base_cost_usd = ((kw.cost_micros or 500_000_000) / 1_000_000) / 90

        for day_offset in range(90):
            d = date.today() - timedelta(days=day_offset)
            trend_factor = 1 + (90 - day_offset) * 0.003
            dow_factor = 0.65 if d.weekday() >= 5 else 1.0
            noise = RNG.uniform(0.3, 1.7)

            clicks = max(0, int(base_clicks * trend_factor * dow_factor * noise))
            impressions = int(max(clicks * RNG.uniform(8, 25), 1)) if clicks > 0 else RNG.randint(3, 40)
            cost_usd = round(clicks * RNG.uniform(0.5, 4.5) * dow_factor, 2) if clicks > 0 else 0
            conversions = 0.0 if is_waste else round(max(0.0, clicks * RNG.uniform(0.0, 0.12)), 2)
            conv_value = round(conversions * RNG.uniform(80, 250), 2)

            kd = KeywordDaily(
                keyword_id=kw.id,
                date=d,
                clicks=clicks,
                impressions=impressions,
                cost_micros=int(cost_usd * 1_000_000),
                conversions=conversions,
                conversion_value_micros=int(conv_value * 1_000_000),
                avg_cpc_micros=int((cost_usd / clicks) * 1_000_000) if clicks > 0 else 0,
            )
            db.add(kd)
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

    # Date range buckets for search terms — spread across different periods
    # so date filtering actually produces different results
    date_buckets = [
        (timedelta(days=7), timedelta(days=0)),     # last 7 days
        (timedelta(days=14), timedelta(days=7)),    # 7-14 days ago
        (timedelta(days=30), timedelta(days=14)),   # 14-30 days ago
        (timedelta(days=60), timedelta(days=30)),   # 30-60 days ago
        (timedelta(days=90), timedelta(days=60)),   # 60-90 days ago
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

            # Pick a random date bucket so filtering by 7d/14d/30d/90d yields different results
            bucket_start, bucket_end = RNG.choice(date_buckets)
            st_date_from = date.today() - bucket_start
            st_date_to = date.today() - bucket_end

            st = SearchTerm(
                ad_group_id=ag.id,
                text=term_text,
                keyword_text=keyword_text,
                clicks=clicks,
                impressions=impressions,
                cost_micros=int(cost * 1_000_000),
                conversions=conversions,
                conversion_value_micros=int(conv_value * 1_000_000),
                ctr=round(clicks / impressions * 100, 2) if impressions else 0.0,
                conversion_rate=round(conversions / clicks * 100, 2) if clicks else 0.0,
                date_from=st_date_from,
                date_to=st_date_to,
                # Extended conversions
                all_conversions=round(conversions * RNG.uniform(1.0, 1.2), 2) if conversions > 0 else None,
                all_conversions_value_micros=int(conv_value * RNG.uniform(1.0, 1.2) * 1_000_000) if conv_value > 0 else None,
                cross_device_conversions=round(conversions * RNG.uniform(0.03, 0.15), 2) if conversions > 0 else None,
                value_per_conversion_micros=int((conv_value / conversions) * 1_000_000) if conversions > 0 else None,
                conversions_value_per_cost=round(conv_value / cost, 2) if cost > 0 else None,
            )
            db.add(st)

    # -----------------------------------------------------------------------
    # PMax Search Terms (no ad_group, linked directly to campaign via campaign_id)
    # -----------------------------------------------------------------------
    pmax_campaign = [c for c in campaigns if c.campaign_type == "PERFORMANCE_MAX"][0]
    pmax_terms = [
        "meble do salonu nowoczesne", "tanie meble online",
        "sklep meblowy internetowy", "meble promocja",
        "meble do małego mieszkania", "meble skandynawskie",
        "komoda drewniana", "regał na książki",
        "meble za darmo oddam",  # Irrelevant
        "jak samemu zrobić meble",  # Informational / irrelevant
    ]
    for term_text in pmax_terms:
        clicks = RNG.randint(5, 120)
        impressions = RNG.randint(clicks * 5, clicks * 25)
        cost = clicks * RNG.uniform(0.5, 3.5)
        conversions = round(RNG.uniform(0, clicks * 0.08), 2)
        conv_value = round(conversions * RNG.uniform(90, 220), 2)

        bucket_start, bucket_end = RNG.choice(date_buckets)
        st_date_from = date.today() - bucket_start
        st_date_to = date.today() - bucket_end

        st = SearchTerm(
            ad_group_id=None,
            campaign_id=pmax_campaign.id,
            text=term_text,
            keyword_text=None,
            source="PMAX",
            clicks=clicks,
            impressions=impressions,
            cost_micros=int(cost * 1_000_000),
            conversions=conversions,
            conversion_value_micros=int(conv_value * 1_000_000),
            ctr=round(clicks / impressions * 100, 2) if impressions else 0.0,
            conversion_rate=round(conversions / clicks * 100, 2) if clicks else 0.0,
            date_from=st_date_from,
            date_to=st_date_to,
            all_conversions=round(conversions * RNG.uniform(1.0, 1.2), 2) if conversions > 0 else None,
            all_conversions_value_micros=int(conv_value * RNG.uniform(1.0, 1.2) * 1_000_000) if conv_value > 0 else None,
            cross_device_conversions=round(conversions * RNG.uniform(0.03, 0.15), 2) if conversions > 0 else None,
            value_per_conversion_micros=int((conv_value / conversions) * 1_000_000) if conversions > 0 else None,
            conversions_value_per_cost=round(conv_value / cost, 2) if cost > 0 else None,
        )
        db.add(st)
    db.flush()

    # -----------------------------------------------------------------------
    # Ads (RSA)
    # -----------------------------------------------------------------------
    for ag in all_ad_groups:
        for ad_idx in range(RNG.randint(1, 3)):
            clicks = RNG.randint(50, 1000)
            impressions = RNG.randint(clicks * 8, clicks * 25)
            cost = clicks * RNG.uniform(0.8, 3.5)
            conversions = int(RNG.uniform(0, clicks * 0.08))

            approval = RNG.choices(
                ["APPROVED", "APPROVED_LIMITED", "UNDER_REVIEW", "DISAPPROVED"],
                weights=[70, 10, 10, 10],
                k=1,
            )[0]
            strength = RNG.choices(
                ["EXCELLENT", "GOOD", "AVERAGE", "POOR", "UNRATED"],
                weights=[10, 30, 30, 15, 15],
                k=1,
            )[0]

            ad = Ad(
                ad_group_id=ag.id,
                google_ad_id=str(RNG.randint(50000, 99999)),
                ad_type="RESPONSIVE_SEARCH_AD",
                status="ENABLED",
                approval_status=approval,
                ad_strength=strength,
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
                ctr=round(clicks / impressions * 100, 2) if impressions else 0.0,
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

            # CPA spike for "Meble Biurowe" — last 3 days have near-zero conversions
            # to trigger CPA_SUSTAINED anomaly alert
            if campaign.name == "Meble Biurowe" and day_offset < 3:
                conversions = 0.01
                conv_value = round(conversions * 150, 2)

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
    # MetricSegmented — device breakdown (last 90 days, SEARCH campaigns only)
    # -----------------------------------------------------------------------
    search_campaigns = [c for c in campaigns if c.campaign_type == "SEARCH" and c.status == "ENABLED"]

    for campaign in search_campaigns:
        for day_offset in range(90):
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
    # MetricSegmented — geo breakdown (last 90 days, SEARCH campaigns only)
    # -----------------------------------------------------------------------
    for campaign in search_campaigns:
        for day_offset in range(90):
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

    # -----------------------------------------------------------------------
    # MetricSegmented — hourly breakdown (last 30 days, SEARCH campaigns only)
    # -----------------------------------------------------------------------
    HOUR_PROFILE = {
        0: 0.05, 1: 0.03, 2: 0.02, 3: 0.02, 4: 0.03, 5: 0.05,
        6: 0.10, 7: 0.30, 8: 0.70, 9: 0.90, 10: 1.00, 11: 0.95,
        12: 0.80, 13: 0.75, 14: 0.85, 15: 0.90, 16: 0.95, 17: 1.00,
        18: 0.85, 19: 0.70, 20: 0.55, 21: 0.40, 22: 0.25, 23: 0.12,
    }

    for campaign in search_campaigns:
        for day_offset in range(30):
            d = date.today() - timedelta(days=day_offset)
            dow_factor = 0.7 if d.weekday() >= 5 else 1.0
            total_daily_clicks = int(RNG.randint(80, 250) * dow_factor)

            for hour, weight in HOUR_PROFILE.items():
                hour_clicks = max(0, int(total_daily_clicks * weight * RNG.uniform(0.7, 1.3)))
                if hour_clicks == 0:
                    continue
                hour_impressions = int(hour_clicks * RNG.uniform(8, 20))
                hour_cost = round(hour_clicks * RNG.uniform(0.8, 3.5), 2)
                conv_rate = 0.05 if 9 <= hour <= 18 else 0.01
                hour_conv = round(max(0, hour_clicks * conv_rate * RNG.uniform(0.5, 1.5)), 2)
                hour_cv = round(hour_conv * RNG.uniform(100, 250), 2)

                ms = MetricSegmented(
                    campaign_id=campaign.id,
                    date=d,
                    device=None,
                    geo_city=None,
                    hour_of_day=hour,
                    clicks=hour_clicks,
                    impressions=hour_impressions,
                    ctr=round(hour_clicks / hour_impressions * 100 if hour_impressions else 0, 2),
                    conversions=hour_conv,
                    conversion_value_micros=int(hour_cv * 1_000_000),
                    cost_micros=int(hour_cost * 1_000_000),
                    avg_cpc_micros=int((hour_cost / hour_clicks) * 1_000_000) if hour_clicks else 0,
                    search_impression_share=_rand_is(RNG, 0.20, 0.80),
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

        # Link very few events to action_log entries (most should be unlinked for unified timeline)
        linked_action_id = None
        if i < 2 and i < len(all_action_logs):
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

    # -----------------------------------------------------------------------
    # Alerts (anomaly detection — for monitoring feature testing)
    # -----------------------------------------------------------------------
    alerts_data = [
        Alert(
            client_id=client.id,
            alert_type="SPEND_SPIKE",
            severity="HIGH",
            title="Nagły wzrost kosztów: Łóżka - Generic",
            description="Kampania wydała 3.2x więcej niż proporcjonalny udział w budżecie konta w ciągu ostatnich 24h.",
            metric_value="Spend: 960 zł (avg: 300 zł/dzień)",
            campaign_id=campaigns[1].id,
            created_at=datetime.utcnow() - timedelta(hours=6),
        ),
        Alert(
            client_id=client.id,
            alert_type="CONVERSION_DROP",
            severity="HIGH",
            title="Spadek konwersji: Kanapy - Generic",
            description="Dzienna średnia konwersji spadła z 4.2 do 0.8 w ciągu ostatnich 3 dni.",
            metric_value="Conv: 0.8/dzień (avg: 4.2/dzień)",
            campaign_id=campaigns[2].id,
            created_at=datetime.utcnow() - timedelta(hours=18),
        ),
        Alert(
            client_id=client.id,
            alert_type="CTR_DROP",
            severity="MEDIUM",
            title="Niski CTR: Meble Biurowe",
            description="CTR kampanii spadł poniżej 0.5% przy ponad 1000 wyświetleń dziennie.",
            metric_value="CTR: 0.38% (próg: 0.5%)",
            campaign_id=campaigns[3].id,
            created_at=datetime.utcnow() - timedelta(days=1, hours=4),
        ),
        Alert(
            client_id=client.id,
            alert_type="SPEND_SPIKE",
            severity="MEDIUM",
            title="Wzrost CPC: Branded Search",
            description="Średni CPC wzrósł o 45% w porównaniu do średniej z ostatnich 14 dni.",
            metric_value="CPC: 3.85 zł (avg: 2.65 zł)",
            campaign_id=campaigns[0].id,
            created_at=datetime.utcnow() - timedelta(days=2),
            resolved_at=datetime.utcnow() - timedelta(days=1),  # Already resolved
        ),
        Alert(
            client_id=client.id,
            alert_type="CONVERSION_DROP",
            severity="HIGH",
            title="Brak konwersji: PMax - Meble Ogólne",
            description="Kampania PMax nie wygenerowała żadnej konwersji w ciągu ostatnich 48h mimo wydania 420 zł.",
            metric_value="Conv: 0 (spend: 420 zł / 48h)",
            campaign_id=pmax_campaign.id,
            created_at=datetime.utcnow() - timedelta(hours=12),
        ),
    ]
    for alert in alerts_data:
        db.add(alert)

    # ---- Negative keywords (campaign + ad group level) ----
    search_campaigns_for_neg = [c for c in campaigns if c.campaign_type == "SEARCH"]
    neg_phrases_campaign = [
        ("darmowe", "BROAD"), ("za darmo", "PHRASE"), ("tanie", "BROAD"),
        ("jak zrobić", "PHRASE"), ("DIY", "EXACT"), ("używane", "PHRASE"),
        ("allegro", "EXACT"), ("olx", "EXACT"),
    ]
    neg_count = 0
    for camp in search_campaigns_for_neg[:3]:
        for text, mt in neg_phrases_campaign:
            db.add(NegativeKeyword(
                client_id=client.id, campaign_id=camp.id,
                criterion_kind="NEGATIVE", text=text, match_type=mt,
                negative_scope="CAMPAIGN", status="ENABLED", source="GOOGLE_ADS_SYNC",
            ))
            neg_count += 1

    if all_ad_groups:
        ag_neg_phrases = [("praca", "PHRASE"), ("zatrudnienie", "PHRASE"), ("forum", "EXACT")]
        for text, mt in ag_neg_phrases:
            ag = all_ad_groups[0]
            db.add(NegativeKeyword(
                client_id=client.id, campaign_id=ag.campaign_id, ad_group_id=ag.id,
                criterion_kind="NEGATIVE", text=text, match_type=mt,
                negative_scope="AD_GROUP", status="ENABLED", source="GOOGLE_ADS_SYNC",
            ))
            neg_count += 1

    # ---- Negative keyword lists ----
    nkl_general = NegativeKeywordList(client_id=client.id, name="Ogólne wykluczenia", description="Standardowe wykluczenia dla wszystkich kampanii")
    nkl_brand = NegativeKeywordList(client_id=client.id, name="Konkurencja", description="Nazwy konkurencyjnych marek")
    db.add(nkl_general)
    db.add(nkl_brand)
    db.flush()

    general_items = ["darmowe", "za darmo", "tanie", "jak zrobić", "DIY", "używane", "praca", "zatrudnienie", "forum", "wikipedia"]
    brand_items = ["IKEA", "Agata Meble", "Black Red White", "Bodzio", "Jysk"]
    for text in general_items:
        db.add(NegativeKeywordListItem(list_id=nkl_general.id, text=text, match_type="PHRASE"))
    for text in brand_items:
        db.add(NegativeKeywordListItem(list_id=nkl_brand.id, text=text, match_type="EXACT"))

    # -----------------------------------------------------------------------
    # ConversionAction (GAP 2A-2D: Conversion Data Quality Audit)
    # -----------------------------------------------------------------------
    conv_actions_data = [
        # Primary, well-configured
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9001",
            name="Zakup online", category="PURCHASE", status="ENABLED", type="WEBPAGE",
            primary_for_goal=True, counting_type="ONE_PER_CLICK",
            value_settings_default_value=150.0, value_settings_always_use_default=False,
            attribution_model="DATA_DRIVEN", click_through_lookback_window_days=30,
            view_through_lookback_window_days=1, include_in_conversions_metric=True,
            conversions=124.0, all_conversions=140.0, conversion_value_micros=18_600_000_000,
        ),
        # Primary but zero-value (sabotages tROAS) — GAP 2B
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9002",
            name="Formularz kontaktowy", category="LEAD", status="ENABLED", type="WEBPAGE",
            primary_for_goal=True, counting_type="ONE_PER_CLICK",
            value_settings_default_value=0.0, value_settings_always_use_default=False,
            attribution_model="DATA_DRIVEN", click_through_lookback_window_days=30,
            view_through_lookback_window_days=1, include_in_conversions_metric=True,
            conversions=45.0, all_conversions=52.0, conversion_value_micros=0,
        ),
        # Secondary but included in metric — GAP 2A
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9003",
            name="Zapis do newslettera", category="SIGNUP", status="ENABLED", type="WEBPAGE",
            primary_for_goal=False, counting_type="ONE_PER_CLICK",
            value_settings_default_value=5.0, value_settings_always_use_default=True,
            attribution_model="GOOGLE_ADS_LAST_CLICK", click_through_lookback_window_days=30,
            view_through_lookback_window_days=1, include_in_conversions_metric=True,
            conversions=210.0, all_conversions=220.0, conversion_value_micros=1_050_000_000,
        ),
        # MANY_PER_CLICK for PURCHASE — GAP 2C (double counting risk)
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9004",
            name="Transakcja e-commerce", category="PURCHASE", status="ENABLED", type="WEBPAGE",
            primary_for_goal=True, counting_type="MANY_PER_CLICK",
            value_settings_default_value=0.0, value_settings_always_use_default=False,
            attribution_model="DATA_DRIVEN", click_through_lookback_window_days=90,
            view_through_lookback_window_days=30, include_in_conversions_metric=True,
            conversions=89.0, all_conversions=95.0, conversion_value_micros=13_350_000_000,
        ),
        # Short lookback — GAP 2D
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9005",
            name="Kliknięcie telefonu", category="LEAD", status="ENABLED", type="WEBPAGE",
            primary_for_goal=False, counting_type="ONE_PER_CLICK",
            value_settings_default_value=10.0, value_settings_always_use_default=True,
            attribution_model="GOOGLE_ADS_LAST_CLICK", click_through_lookback_window_days=3,
            view_through_lookback_window_days=1, include_in_conversions_metric=False,
            conversions=18.0, all_conversions=22.0, conversion_value_micros=180_000_000,
        ),
        # Normal secondary
        ConversionAction(
            client_id=client.id, google_conversion_action_id="9006",
            name="Wyświetlenie strony produktu", category="PAGE_VIEW", status="ENABLED", type="WEBPAGE",
            primary_for_goal=False, counting_type="ONE_PER_CLICK",
            value_settings_default_value=0.0, value_settings_always_use_default=False,
            attribution_model="GOOGLE_ADS_LAST_CLICK", click_through_lookback_window_days=30,
            view_through_lookback_window_days=1, include_in_conversions_metric=False,
            conversions=890.0, all_conversions=920.0, conversion_value_micros=0,
        ),
    ]
    for ca in conv_actions_data:
        db.add(ca)

    # -----------------------------------------------------------------------
    # MetricSegmented — age range breakdown (GAP 4A, last 90 days)
    # -----------------------------------------------------------------------
    AGE_RANGES = ["AGE_RANGE_18_24", "AGE_RANGE_25_34", "AGE_RANGE_35_44", "AGE_RANGE_45_54", "AGE_RANGE_55_64", "AGE_RANGE_65_UP", "AGE_RANGE_UNDETERMINED"]
    AGE_WEIGHTS = {"AGE_RANGE_18_24": 0.12, "AGE_RANGE_25_34": 0.28, "AGE_RANGE_35_44": 0.25, "AGE_RANGE_45_54": 0.15, "AGE_RANGE_55_64": 0.10, "AGE_RANGE_65_UP": 0.05, "AGE_RANGE_UNDETERMINED": 0.05}
    # Make 18-24 have very high CPA (anomaly) and 65+ very low conv rate
    AGE_CONV_MULT = {"AGE_RANGE_18_24": 0.15, "AGE_RANGE_25_34": 1.2, "AGE_RANGE_35_44": 1.0, "AGE_RANGE_45_54": 0.8, "AGE_RANGE_55_64": 0.5, "AGE_RANGE_65_UP": 0.2, "AGE_RANGE_UNDETERMINED": 0.3}

    for campaign in search_campaigns:
        for day_offset in range(90):
            d = date.today() - timedelta(days=day_offset)
            dow_factor = 0.7 if d.weekday() >= 5 else 1.0
            total_clicks = int(RNG.randint(40, 180) * dow_factor)

            for age in AGE_RANGES:
                w = AGE_WEIGHTS[age]
                a_clicks = max(1, int(total_clicks * w * RNG.uniform(0.6, 1.4)))
                a_impr = int(a_clicks * RNG.uniform(8, 22))
                a_cost = round(a_clicks * RNG.uniform(0.8, 3.5), 2)
                conv_mult = AGE_CONV_MULT[age]
                a_conv = round(max(0.0, a_clicks * RNG.uniform(0.01, 0.06) * conv_mult), 2)
                a_cv = round(a_conv * RNG.uniform(100, 250), 2)

                db.add(MetricSegmented(
                    campaign_id=campaign.id, date=d, age_range=age,
                    clicks=a_clicks, impressions=a_impr,
                    ctr=round(a_clicks / a_impr * 100 if a_impr else 0, 2),
                    conversions=a_conv,
                    conversion_value_micros=int(a_cv * 1_000_000),
                    cost_micros=int(a_cost * 1_000_000),
                    avg_cpc_micros=int((a_cost / a_clicks) * 1_000_000) if a_clicks else 0,
                ))

    # -----------------------------------------------------------------------
    # MetricSegmented — gender breakdown (GAP 4A, last 90 days)
    # -----------------------------------------------------------------------
    GENDERS = ["MALE", "FEMALE", "UNDETERMINED"]
    GENDER_WEIGHTS = {"MALE": 0.42, "FEMALE": 0.48, "UNDETERMINED": 0.10}
    GENDER_CONV_MULT = {"MALE": 0.9, "FEMALE": 1.1, "UNDETERMINED": 0.4}

    for campaign in search_campaigns:
        for day_offset in range(90):
            d = date.today() - timedelta(days=day_offset)
            dow_factor = 0.7 if d.weekday() >= 5 else 1.0
            total_clicks = int(RNG.randint(40, 180) * dow_factor)

            for gender in GENDERS:
                w = GENDER_WEIGHTS[gender]
                g_clicks = max(1, int(total_clicks * w * RNG.uniform(0.6, 1.4)))
                g_impr = int(g_clicks * RNG.uniform(8, 22))
                g_cost = round(g_clicks * RNG.uniform(0.8, 3.5), 2)
                conv_mult = GENDER_CONV_MULT[gender]
                g_conv = round(max(0.0, g_clicks * RNG.uniform(0.01, 0.06) * conv_mult), 2)
                g_cv = round(g_conv * RNG.uniform(100, 250), 2)

                db.add(MetricSegmented(
                    campaign_id=campaign.id, date=d, gender=gender,
                    clicks=g_clicks, impressions=g_impr,
                    ctr=round(g_clicks / g_impr * 100 if g_impr else 0, 2),
                    conversions=g_conv,
                    conversion_value_micros=int(g_cv * 1_000_000),
                    cost_micros=int(g_cost * 1_000_000),
                    avg_cpc_micros=int((g_cost / g_clicks) * 1_000_000) if g_clicks else 0,
                ))

    db.commit()
    db.close()

    print("Done! Demo data seeded successfully!")
    print("   - 1 client (Demo Meble)")
    print(f"   - {len(campaigns)} campaigns (with IS + Smart Bidding targets + learning status)")
    print(f"   - {len(all_ad_groups)} ad groups")
    print("   - Keywords (with IS, QS historical, extended conv, top impression %)")
    print(f"   - Search terms (with extended conversions + {len(pmax_terms)} PMax terms)")
    print("   - 90 days of daily metrics (with IS, extended conv, top impression %)")
    print("   - 90 days of device breakdown (MetricSegmented)")
    print("   - 90 days of geo breakdown (MetricSegmented)")
    print("   - 90 days of age/gender breakdown (MetricSegmented)")
    print(f"   - {len(conv_actions_data)} conversion actions (quality audit data)")
    print(f"   - {len(all_action_logs)} action log entries")
    print(f"   - {len(change_events_data)} change events (external history)")
    print(f"   - {len(alerts_data)} alerts (anomaly detection)")


if __name__ == "__main__":
    seed_demo_data()
