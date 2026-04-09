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
from app.models.placement_exclusion_list import PlacementExclusionList, PlacementExclusionListItem
from app.models.asset_group import AssetGroup
from app.models.asset_group_daily import AssetGroupDaily
from app.models.asset_group_asset import AssetGroupAsset
from app.models.asset_group_signal import AssetGroupSignal
from app.models.campaign_audience import CampaignAudienceMetric
from app.models.campaign_asset import CampaignAsset
from app.models.report import Report
from app.models.auction_insight import AuctionInsight
from app.models.product_group import ProductGroup
from app.models.placement import Placement
from app.models.bid_modifier import BidModifier
from app.models.audience import Audience
from app.models.topic import TopicPerformance
from app.models.bidding_strategy import BiddingStrategy, SharedBudget
from app.models.google_recommendation import GoogleRecommendation
from app.models.dsa_target import DsaTarget
from app.models.dsa_headline import DsaHeadline


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
        ("Display - Remarketing", "DISPLAY", 80, "ENABLED", "MAXIMIZE_CONVERSIONS"),
        ("PMax - Meble Ogólne", "PERFORMANCE_MAX", 350, "ENABLED", "MAXIMIZE_CONVERSION_VALUE"),
        ("Kanapy - Retarget", "SEARCH", 120, "ENABLED", "TARGET_CPA"),  # portfolio member
        ("Video - YouTube Meble", "VIDEO", 60, "ENABLED", "TARGET_CPA"),
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
    # Auction Insights (competitor visibility — Search campaigns only)
    # -----------------------------------------------------------------------
    COMPETITOR_DOMAINS = [
        "meble-online.pl", "ikea.pl", "brw.com.pl", "agata.pl",
        "mebleportfolio.pl", "leroymerlin.pl", "empik.com",
    ]
    search_campaigns = [c for c in campaigns if c.campaign_type == "SEARCH" and c.status != "PAUSED"]
    for campaign in search_campaigns:
        # Each campaign sees 3-5 competitors
        n_competitors = RNG.randint(3, min(5, len(COMPETITOR_DOMAINS)))
        camp_competitors = RNG.sample(COMPETITOR_DOMAINS, n_competitors)

        for day_offset in range(30):
            d = date.today() - timedelta(days=day_offset)
            # "You" entry
            db.add(AuctionInsight(
                campaign_id=campaign.id,
                date=d,
                display_domain="demo-meble.pl",
                impression_share=round(RNG.uniform(0.15, 0.45), 4),
                overlap_rate=1.0,
                position_above_rate=0.0,
                outranking_share=round(RNG.uniform(0.20, 0.55), 4),
                top_of_page_rate=round(RNG.uniform(0.30, 0.70), 4),
                abs_top_of_page_rate=round(RNG.uniform(0.10, 0.35), 4),
            ))
            # Competitors
            for domain in camp_competitors:
                db.add(AuctionInsight(
                    campaign_id=campaign.id,
                    date=d,
                    display_domain=domain,
                    impression_share=round(RNG.uniform(0.05, 0.60), 4),
                    overlap_rate=round(RNG.uniform(0.20, 0.80), 4),
                    position_above_rate=round(RNG.uniform(0.10, 0.60), 4),
                    outranking_share=round(RNG.uniform(0.10, 0.50), 4),
                    top_of_page_rate=round(RNG.uniform(0.15, 0.65), 4),
                    abs_top_of_page_rate=round(RNG.uniform(0.05, 0.30), 4),
                ))
    db.flush()

    # -----------------------------------------------------------------------
    # Product Groups (Shopping campaign — tree structure)
    # -----------------------------------------------------------------------
    shopping_campaigns = [c for c in campaigns if c.campaign_type == "SHOPPING"]
    PRODUCT_BRANDS = ["Demo Meble", "Ikea", "BRW", "Agata"]
    PRODUCT_TYPES = ["Łóżka", "Kanapy", "Stoły", "Krzesła", "Biurka"]
    for camp in shopping_campaigns:
        ag = db.query(AdGroup).filter(AdGroup.campaign_id == camp.id).first()
        ag_id = ag.id if ag else None
        # Root node
        db.add(ProductGroup(campaign_id=camp.id, ad_group_id=ag_id, google_criterion_id="PG_ROOT",
            partition_type="SUBDIVISION", case_value_type=None, case_value=None,
            clicks=sum(RNG.randint(50, 200) for _ in range(5)), impressions=RNG.randint(5000, 20000),
            cost_micros=RNG.randint(3000, 8000) * 1_000_000, conversions=round(RNG.uniform(20, 80), 1),
            conversion_value_micros=RNG.randint(10000, 50000) * 1_000_000, ctr=round(RNG.uniform(2, 6), 2)))
        for i, brand in enumerate(PRODUCT_BRANDS):
            clicks = RNG.randint(30, 150)
            cost = round(clicks * RNG.uniform(1.5, 3.5), 2)
            convs = round(clicks * RNG.uniform(0.03, 0.12), 1)
            db.add(ProductGroup(campaign_id=camp.id, ad_group_id=ag_id,
                google_criterion_id=f"PG_BRAND_{i}", parent_criterion_id="PG_ROOT",
                partition_type="UNIT", case_value_type="PRODUCT_BRAND", case_value=brand,
                bid_micros=int(RNG.uniform(1.0, 3.0) * 1_000_000),
                clicks=clicks, impressions=int(clicks * RNG.uniform(12, 25)),
                cost_micros=int(cost * 1_000_000), conversions=convs,
                conversion_value_micros=int(convs * RNG.uniform(100, 300) * 1_000_000),
                ctr=round(RNG.uniform(3, 7), 2)))
        for i, ptype in enumerate(PRODUCT_TYPES):
            clicks = RNG.randint(20, 100)
            cost = round(clicks * RNG.uniform(1.0, 2.5), 2)
            convs = round(clicks * RNG.uniform(0.02, 0.10), 1)
            db.add(ProductGroup(campaign_id=camp.id, ad_group_id=ag_id,
                google_criterion_id=f"PG_TYPE_{i}", parent_criterion_id="PG_ROOT",
                partition_type="UNIT", case_value_type="PRODUCT_TYPE", case_value=ptype,
                bid_micros=int(RNG.uniform(0.8, 2.5) * 1_000_000),
                clicks=clicks, impressions=int(clicks * RNG.uniform(15, 30)),
                cost_micros=int(cost * 1_000_000), conversions=convs,
                conversion_value_micros=int(convs * RNG.uniform(80, 250) * 1_000_000),
                ctr=round(RNG.uniform(2, 5), 2)))
    db.flush()

    # -----------------------------------------------------------------------
    # Placements (Display + Video campaigns)
    # -----------------------------------------------------------------------
    PLACEMENT_URLS = [
        ("onet.pl", "WEBSITE"), ("wp.pl", "WEBSITE"), ("allegro.pl", "WEBSITE"),
        ("meble-inspiracje.pl", "WEBSITE"), ("domowe-wnetrza.pl", "WEBSITE"),
        ("youtube.com/channel/UC_meble", "YOUTUBE_CHANNEL"),
        ("youtube.com/watch?v=abc123", "YOUTUBE_VIDEO"),
        ("play.google.com/store/apps/details?id=meble.app", "MOBILE_APP"),
    ]
    display_video_campaigns = [c for c in campaigns if c.campaign_type in ("DISPLAY", "VIDEO") and c.status == "ENABLED"]
    for camp in display_video_campaigns:
        is_video = camp.campaign_type == "VIDEO"
        for day_offset in range(30):
            d = date.today() - timedelta(days=day_offset)
            n_placements = RNG.randint(3, min(6, len(PLACEMENT_URLS)))
            for url, ptype in RNG.sample(PLACEMENT_URLS, n_placements):
                clicks = RNG.randint(5, 80)
                impressions = int(clicks * RNG.uniform(20, 60))
                cost = round(clicks * RNG.uniform(0.3, 2.0), 2)
                convs = round(max(0, clicks * RNG.uniform(-0.01, 0.05)), 2)
                db.add(Placement(campaign_id=camp.id, date=d,
                    placement_url=url, placement_type=ptype, display_name=url.split("/")[0],
                    clicks=clicks, impressions=impressions, cost_micros=int(cost * 1_000_000),
                    conversions=convs, conversion_value_micros=int(convs * RNG.uniform(50, 200) * 1_000_000),
                    ctr=round(clicks / impressions * 100, 2) if impressions else 0,
                    video_views=RNG.randint(100, 5000) if is_video else None,
                    video_view_rate=round(RNG.uniform(15, 45), 1) if is_video else None,
                    avg_cpv_micros=int(RNG.uniform(0.02, 0.10) * 1_000_000) if is_video else None))
    db.flush()

    # -----------------------------------------------------------------------
    # Topics (Display/Video campaigns)
    # -----------------------------------------------------------------------
    TOPICS = [
        ("Arts & Entertainment > Home & Garden", "1001"), ("Shopping > Furniture", "1002"),
        ("Home & Garden > Home Furnishings", "1003"), ("Real Estate > Property", "1004"),
        ("Business > Interior Design", "1005"), ("Lifestyle > Home Decor", "1006"),
    ]
    for camp in display_video_campaigns:
        for day_offset in range(0, 30, 3):
            d = date.today() - timedelta(days=day_offset)
            for topic_path, topic_id in RNG.sample(TOPICS, RNG.randint(3, len(TOPICS))):
                clicks = RNG.randint(10, 60)
                cost = round(clicks * RNG.uniform(0.5, 2.0), 2)
                convs = round(max(0, clicks * RNG.uniform(-0.01, 0.04)), 2)
                db.add(TopicPerformance(campaign_id=camp.id, date=d,
                    topic_id=topic_id, topic_path=topic_path,
                    bid_modifier=round(RNG.uniform(0.8, 1.5), 2),
                    clicks=clicks, impressions=int(clicks * RNG.uniform(20, 50)),
                    cost_micros=int(cost * 1_000_000), conversions=convs,
                    conversion_value_micros=int(convs * RNG.uniform(60, 200) * 1_000_000),
                    ctr=round(RNG.uniform(1, 5), 2)))
    db.flush()

    # -----------------------------------------------------------------------
    # Bid Modifiers (device + location + schedule for all campaigns)
    # -----------------------------------------------------------------------
    for camp in campaigns:
        if camp.status == "PAUSED":
            continue
        # Device modifiers
        for device, mod in [("MOBILE", round(RNG.uniform(0.7, 1.3), 2)),
                            ("DESKTOP", 1.0),
                            ("TABLET", round(RNG.uniform(0.5, 1.0), 2))]:
            db.add(BidModifier(campaign_id=camp.id, modifier_type="DEVICE",
                device_type=device, bid_modifier=mod,
                google_criterion_id=str(RNG.randint(90000, 99999))))
        # Location modifiers (Warszawa +20%, reszta neutral)
        db.add(BidModifier(campaign_id=camp.id, modifier_type="LOCATION",
            location_id="1011078", location_name="Warszawa", bid_modifier=1.2,
            google_criterion_id=str(RNG.randint(90000, 99999))))
        db.add(BidModifier(campaign_id=camp.id, modifier_type="LOCATION",
            location_id="1011053", location_name="Kraków", bid_modifier=1.1,
            google_criterion_id=str(RNG.randint(90000, 99999))))
        # Ad schedule (weekdays boost, weekends reduce)
        for dow in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
            db.add(BidModifier(campaign_id=camp.id, modifier_type="AD_SCHEDULE",
                day_of_week=dow, start_hour=9, end_hour=18,
                bid_modifier=1.15, google_criterion_id=str(RNG.randint(90000, 99999))))
        for dow in ["SATURDAY", "SUNDAY"]:
            db.add(BidModifier(campaign_id=camp.id, modifier_type="AD_SCHEDULE",
                day_of_week=dow, start_hour=10, end_hour=16,
                bid_modifier=0.75, google_criterion_id=str(RNG.randint(90000, 99999))))
    db.flush()

    # -----------------------------------------------------------------------
    # Audiences (remarketing, in-market, affinity)
    # -----------------------------------------------------------------------
    AUDIENCE_DATA = [
        ("Remarketing - Odwiedzający stronę", "REMARKETING", 45000),
        ("Remarketing - Porzucone koszyki", "REMARKETING", 12000),
        ("In-market - Meble do salonu", "IN_MARKET", 350000),
        ("In-market - Wyposażenie domu", "IN_MARKET", 520000),
        ("Affinity - Entuzjaści designu", "AFFINITY", 1200000),
        ("Affinity - Właściciele domów", "AFFINITY", 890000),
        ("Custom - Szukający łóżek 160x200", "CUSTOM_INTENT", 28000),
    ]
    for name, atype, members in AUDIENCE_DATA:
        db.add(Audience(client_id=client.id, google_audience_id=str(RNG.randint(100000, 999999)),
            name=name, audience_type=atype, status="ENABLED", member_count=members))
    db.flush()

    # -----------------------------------------------------------------------
    # Google Recommendations (native Google suggestions)
    # -----------------------------------------------------------------------
    RECO_TYPES = [
        ("KEYWORD", "Branded Search", "Dodaj nowe słowa kluczowe"),
        ("SITELINK_EXTENSION", "Łóżka - Generic", "Dodaj rozszerzenia sitelink"),
        ("RESPONSIVE_SEARCH_AD", "Kanapy - Generic", "Dodaj więcej nagłówków RSA"),
        ("TARGET_CPA_OPT_IN", "Meble Biurowe", "Przejdź na Target CPA"),
        ("CALLOUT_EXTENSION", "Branded Search", "Dodaj rozszerzenia callout"),
        ("KEYWORD", "Shopping - Łóżka", "Rozszerz listę słów kluczowych"),
        ("MAXIMIZE_CONVERSIONS_OPT_IN", "Display - Remarketing", "Włącz Maximize Conversions"),
        ("VIDEO_OUTSTREAM", "Video - YouTube Meble", "Dodaj reklamy outstream"),
    ]
    for rtype, camp_name, desc in RECO_TYPES:
        camp = next((c for c in campaigns if c.name == camp_name), None)
        db.add(GoogleRecommendation(client_id=client.id, campaign_id=camp.id if camp else None,
            google_recommendation_id=str(RNG.randint(100000, 999999)),
            recommendation_type=rtype, description=desc, campaign_name=camp_name,
            impact_estimate={"base": {"conversions": RNG.randint(5, 30)},
                             "potential": {"conversions": RNG.randint(10, 50)}},
            status="ACTIVE"))
    db.flush()

    # -----------------------------------------------------------------------
    # Bidding Strategies (portfolio strategies)
    # -----------------------------------------------------------------------
    db.add(BiddingStrategy(client_id=client.id, google_strategy_id="777",
        resource_name="customers/1234567890/biddingStrategies/777",
        name="Portfolio Kanapy tCPA", strategy_type="TARGET_CPA",
        target_cpa_micros=35_000_000, campaign_count=2))
    db.add(BiddingStrategy(client_id=client.id, google_strategy_id="888",
        resource_name="customers/1234567890/biddingStrategies/888",
        name="Portfolio Shopping tROAS", strategy_type="TARGET_ROAS",
        target_roas=3.5, campaign_count=1))
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

    # ---- MCC-level exclusion lists (owned by manager account) ----
    mcc_nkl_profanity = NegativeKeywordList(
        client_id=client.id, name="Wulgaryzmy i spam",
        description="Wykluczenia MCC — przekleństwa, treści dla dorosłych, spam",
        source="MCC_SYNC", ownership_level="mcc",
    )
    mcc_nkl_irrelevant = NegativeKeywordList(
        client_id=client.id, name="Nieistotne intencje",
        description="Wykluczenia MCC — frazy informacyjne bez intencji zakupowej",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(mcc_nkl_profanity)
    db.add(mcc_nkl_irrelevant)
    db.flush()

    profanity_items = ["kurwa", "cholera", "porno", "xxx", "sex", "nude", "hack", "crack", "torrent", "pirat"]
    irrelevant_items = ["jak zrobić", "co to jest", "definicja", "wikipedia", "referat", "praca magisterska",
                        "darmowe", "free download", "za darmo", "piracki", "chomikuj", "zalukaj"]
    for text in profanity_items:
        db.add(NegativeKeywordListItem(list_id=mcc_nkl_profanity.id, text=text, match_type="BROAD"))
    for text in irrelevant_items:
        db.add(NegativeKeywordListItem(list_id=mcc_nkl_irrelevant.id, text=text, match_type="PHRASE"))

    # MCC-level placement exclusion lists
    mcc_pel_spam = PlacementExclusionList(
        client_id=client.id, name="Spammerskie strony",
        description="Wykluczenia MCC — strony z reklamami, click-bait, made-for-ads",
        source="MCC_SYNC", ownership_level="mcc",
    )
    mcc_pel_apps = PlacementExclusionList(
        client_id=client.id, name="Niechciane aplikacje",
        description="Wykluczenia MCC — gry i aplikacje o niskiej jakości ruchu",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(mcc_pel_spam)
    db.add(mcc_pel_apps)
    db.flush()

    spam_sites = [
        ("clickbait-news24.com", "WEBSITE"), ("made-for-ads-site.net", "WEBSITE"),
        ("spammy-recipes.info", "WEBSITE"), ("fake-celebrity-news.com", "WEBSITE"),
        ("download-free-stuff.xyz", "WEBSITE"), ("auto-redirect-ads.com", "WEBSITE"),
        ("cheap-traffic-network.com", "WEBSITE"), ("popup-generator.net", "WEBSITE"),
        ("low-quality-content.org", "WEBSITE"), ("adsense-farm-123.com", "WEBSITE"),
        ("youtube.com/channel/UCspam_channel_fake1", "YOUTUBE_CHANNEL"),
        ("youtube.com/channel/UCspam_channel_fake2", "YOUTUBE_CHANNEL"),
    ]
    app_exclusions = [
        ("play.google.com/store/apps/details?id=com.bad.game1", "MOBILE_APP"),
        ("play.google.com/store/apps/details?id=com.bad.game2", "MOBILE_APP"),
        ("play.google.com/store/apps/details?id=com.clickfraud.app", "MOBILE_APP"),
        ("play.google.com/store/apps/details?id=com.lowquality.tool", "MOBILE_APP"),
    ]
    for url, ptype in spam_sites:
        db.add(PlacementExclusionListItem(list_id=mcc_pel_spam.id, url=url, placement_type=ptype))
    for url, ptype in app_exclusions:
        db.add(PlacementExclusionListItem(list_id=mcc_pel_apps.id, url=url, placement_type=ptype))

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

    # -----------------------------------------------------------------------
    # Phase D: PMax Channel Breakdown (GAP 3A)
    # -----------------------------------------------------------------------
    today = date.today()
    pmax_campaign = [c for c in campaigns if c.campaign_type == "PERFORMANCE_MAX"][0]
    NETWORK_TYPES = ["SEARCH", "CONTENT", "YOUTUBE_WATCH", "SHOPPING", "CROSS_NETWORK"]
    NETWORK_WEIGHTS = [0.40, 0.20, 0.15, 0.20, 0.05]

    for day_offset in range(90):
        d = today - timedelta(days=day_offset)
        dow_factor = 0.8 if d.weekday() >= 5 else 1.0
        for net_type, weight in zip(NETWORK_TYPES, NETWORK_WEIGHTS):
            base_impr = int(RNG.gauss(1200, 300) * weight * dow_factor)
            base_impr = max(10, base_impr)
            base_ctr = RNG.uniform(0.02, 0.08)
            base_clicks = max(1, int(base_impr * base_ctr))
            base_cost = base_clicks * RNG.uniform(0.5, 2.5)
            conv_rate = RNG.uniform(0.02, 0.07)
            if net_type == "CROSS_NETWORK":
                conv_rate *= 0.3  # low conversions for cross-network
            base_conv = round(max(0, base_clicks * conv_rate), 2)
            base_cv = round(base_conv * RNG.uniform(80, 200), 2)

            db.add(MetricSegmented(
                campaign_id=pmax_campaign.id,
                date=d,
                ad_network_type=net_type,
                clicks=base_clicks,
                impressions=base_impr,
                ctr=round(base_clicks / base_impr * 100, 2) if base_impr else 0,
                conversions=base_conv,
                conversion_value_micros=int(base_cv * 1_000_000),
                cost_micros=int(base_cost * 1_000_000),
                avg_cpc_micros=int((base_cost / base_clicks) * 1_000_000) if base_clicks else 0,
            ))

    db.flush()

    # -----------------------------------------------------------------------
    # Phase D: Asset Groups + Daily + Assets + Signals (GAP 3B, 3C)
    # -----------------------------------------------------------------------
    asset_groups_data = [
        ("Meble - Ogólne", "GOOD", "https://demo-meble.pl/meble", 5001),
        ("Kanapy Premium", "EXCELLENT", "https://demo-meble.pl/kanapy-premium", 5002),
        ("Promocje Sezonowe", "POOR", "https://demo-meble.pl/promocje", 5003),
    ]

    asset_groups = []
    for ag_name, ad_strength, url, gid in asset_groups_data:
        ag = AssetGroup(
            campaign_id=pmax_campaign.id,
            google_asset_group_id=str(gid),
            name=ag_name,
            status="ENABLED",
            ad_strength=ad_strength,
            final_url=url,
            path1="meble",
            path2=ag_name.split(" - ")[-1].lower() if " - " in ag_name else "",
        )
        db.add(ag)
        asset_groups.append(ag)
    db.flush()

    # Daily metrics per asset group (90 days)
    for ag_idx, ag in enumerate(asset_groups):
        base_mult = [1.0, 1.3, 0.6][ag_idx]
        for day_offset in range(90):
            d = today - timedelta(days=day_offset)
            dow_factor = 0.75 if d.weekday() >= 5 else 1.0
            impr = max(10, int(RNG.gauss(800, 200) * base_mult * dow_factor))
            ctr_val = RNG.uniform(0.03, 0.08)
            clicks = max(1, int(impr * ctr_val))
            cost = clicks * RNG.uniform(0.8, 2.0) * base_mult
            conv = round(max(0, clicks * RNG.uniform(0.03, 0.08)), 2)
            cv = round(conv * RNG.uniform(100, 250), 2)

            db.add(AssetGroupDaily(
                asset_group_id=ag.id,
                date=d,
                clicks=clicks,
                impressions=impr,
                ctr=round(clicks / impr * 100, 2) if impr else 0,
                conversions=conv,
                conversion_value_micros=int(cv * 1_000_000),
                cost_micros=int(cost * 1_000_000),
                avg_cpc_micros=int((cost / clicks) * 1_000_000) if clicks else 0,
            ))

    db.flush()

    # Assets per asset group (8-12 each)
    asset_templates = {
        "Meble - Ogólne": [
            ("HEADLINE", "HEADLINE", "Meble najwyższej jakości", "BEST"),
            ("HEADLINE", "HEADLINE", "Darmowa dostawa od 500 zł", "GOOD"),
            ("HEADLINE", "HEADLINE", "Sprawdź naszą kolekcję", "LOW"),
            ("LONG_HEADLINE", "LONG_HEADLINE", "Meble premium z darmową dostawą w 24h", "GOOD"),
            ("DESCRIPTION", "DESCRIPTION", "Ponad 5000 mebli w ofercie. Gwarancja jakości.", "BEST"),
            ("DESCRIPTION", "DESCRIPTION", "Wygodne raty 0%. Zamów online.", "GOOD"),
            ("IMAGE", "MARKETING_IMAGE", None, "GOOD"),
            ("IMAGE", "SQUARE_MARKETING_IMAGE", None, "LEARNING"),
            ("YOUTUBE_VIDEO", "YOUTUBE_VIDEO", None, "LOW"),
        ],
        "Kanapy Premium": [
            ("HEADLINE", "HEADLINE", "Kanapy premium od 2999 zł", "BEST"),
            ("HEADLINE", "HEADLINE", "Skórzane sofy — nowa kolekcja", "BEST"),
            ("HEADLINE", "HEADLINE", "Komfort na lata", "GOOD"),
            ("LONG_HEADLINE", "LONG_HEADLINE", "Eleganckie kanapy premium — darmowy transport", "BEST"),
            ("DESCRIPTION", "DESCRIPTION", "Najlepsza jakość skóry naturalnej. 10 lat gwarancji.", "BEST"),
            ("DESCRIPTION", "DESCRIPTION", "Kanapy narożne, rozkładane, 2-os i 3-os.", "GOOD"),
            ("IMAGE", "MARKETING_IMAGE", None, "BEST"),
            ("IMAGE", "SQUARE_MARKETING_IMAGE", None, "GOOD"),
            ("IMAGE", "LOGO", None, "GOOD"),
            ("YOUTUBE_VIDEO", "YOUTUBE_VIDEO", None, "GOOD"),
        ],
        "Promocje Sezonowe": [
            ("HEADLINE", "HEADLINE", "Wyprzedaż do -50%", "LOW"),
            ("HEADLINE", "HEADLINE", "Ostatnie sztuki", "LEARNING"),
            ("LONG_HEADLINE", "LONG_HEADLINE", "Wielka wyprzedaż mebli — rabaty do 50%", "LOW"),
            ("DESCRIPTION", "DESCRIPTION", "Wyprzedaż trwa do końca miesiąca.", "LOW"),
            ("DESCRIPTION", "DESCRIPTION", "Kup teraz — limitowana oferta.", "LEARNING"),
            ("IMAGE", "MARKETING_IMAGE", None, "LOW"),
            ("IMAGE", "SQUARE_MARKETING_IMAGE", None, "LEARNING"),
            ("YOUTUBE_VIDEO", "YOUTUBE_VIDEO", None, "LEARNING"),
        ],
    }

    asset_id_counter = 9000
    for ag in asset_groups:
        templates = asset_templates.get(ag.name, [])
        for at_type, at_field, at_text, at_perf in templates:
            asset_id_counter += 1
            db.add(AssetGroupAsset(
                asset_group_id=ag.id,
                google_asset_id=str(asset_id_counter),
                asset_type=at_type,
                field_type=at_field,
                text_content=at_text,
                performance_label=at_perf,
            ))

    db.flush()

    # Signals per asset group (search themes + audience)
    signal_data = {
        "Meble - Ogólne": [
            ("SEARCH_THEME", "meble do domu", "", ""),
            ("SEARCH_THEME", "sklep meblowy online", "", ""),
            ("SEARCH_THEME", "meble pokojowe", "", ""),
            ("AUDIENCE", "", "customers/123/userLists/1001", "Remarketing - Odwiedzający"),
            ("AUDIENCE", "", "customers/123/userLists/1002", "Podobni - Kupujący"),
        ],
        "Kanapy Premium": [
            ("SEARCH_THEME", "kanapy skórzane", "", ""),
            ("SEARCH_THEME", "sofa narożna", "", ""),
            ("SEARCH_THEME", "meble premium", "", ""),
            ("SEARCH_THEME", "kanapa rozkładana", "", ""),
            ("AUDIENCE", "", "customers/123/userLists/1003", "In-Market - Meble"),
        ],
        "Promocje Sezonowe": [
            ("SEARCH_THEME", "wyprzedaż mebli", "", ""),
            ("SEARCH_THEME", "meble promocja", "", ""),
            ("SEARCH_THEME", "tanie meble", "", ""),
            ("AUDIENCE", "", "customers/123/userLists/1001", "Remarketing - Odwiedzający"),
            ("AUDIENCE", "", "customers/123/userLists/1004", "Custom - Szukający rabatów"),
        ],
    }

    for ag in asset_groups:
        signals = signal_data.get(ag.name, [])
        for sig_type, theme_text, aud_rn, aud_name in signals:
            db.add(AssetGroupSignal(
                asset_group_id=ag.id,
                signal_type=sig_type,
                search_theme_text=theme_text,
                audience_resource_name=aud_rn,
                audience_name=aud_name,
            ))

    db.flush()

    # -----------------------------------------------------------------------
    # Phase D: Campaign Audience Metrics (GAP 4B)
    # -----------------------------------------------------------------------
    search_campaigns_for_audience = [c for c in campaigns if c.campaign_type == "SEARCH" and c.status == "ENABLED"]

    audience_defs = [
        ("customers/123/userLists/2001", "Remarketing - Kupujący 30d", "REMARKETING", 1.3),
        ("customers/123/userLists/2002", "In-Market - Meble domowe", "IN_MARKET", 0.9),
        ("customers/123/userLists/2003", "In-Market - Wyposażenie wnętrz", "IN_MARKET", 0.5),
        ("customers/123/userLists/2004", "Affinity - Design Lovers", "AFFINITY", 0.7),
        ("customers/123/userLists/2005", "Custom - Szukający mebli premium", "CUSTOM", 1.1),
    ]

    for camp in search_campaigns_for_audience[:2]:  # first 2 SEARCH campaigns
        for aud_rn, aud_name, aud_type, conv_mult in audience_defs:
            for day_offset in range(90):
                d = today - timedelta(days=day_offset)
                dow_factor = 0.75 if d.weekday() >= 5 else 1.0
                base_impr = max(5, int(RNG.gauss(200, 50) * dow_factor))
                base_ctr = RNG.uniform(0.02, 0.06)
                base_clicks = max(0, int(base_impr * base_ctr))
                if base_clicks == 0:
                    continue
                base_cost = base_clicks * RNG.uniform(0.8, 2.5)
                base_conv = round(max(0, base_clicks * RNG.uniform(0.02, 0.06) * conv_mult), 2)
                base_cv = round(base_conv * RNG.uniform(100, 300), 2)

                db.add(CampaignAudienceMetric(
                    campaign_id=camp.id,
                    audience_resource_name=aud_rn,
                    audience_name=aud_name,
                    audience_type=aud_type,
                    date=d,
                    clicks=base_clicks,
                    impressions=base_impr,
                    ctr=round(base_clicks / base_impr * 100, 2) if base_impr else 0,
                    conversions=base_conv,
                    conversion_value_micros=int(base_cv * 1_000_000),
                    cost_micros=int(base_cost * 1_000_000),
                    avg_cpc_micros=int((base_cost / base_clicks) * 1_000_000) if base_clicks else 0,
                    bid_modifier=round(RNG.uniform(0.8, 1.5), 2) if aud_type == "REMARKETING" else None,
                ))

        if (day_offset + 1) % 30 == 0:
            db.flush()

    db.flush()

    # -----------------------------------------------------------------------
    # Phase D: Campaign Assets / Extensions (GAP 5A + 5B)
    # -----------------------------------------------------------------------
    extension_configs = {
        "Branded Search": {
            "SITELINK": [
                ("Kolekcje", "Najnowsze kolekcje mebli", "BEST"),
                ("Wyprzedaż", "Rabaty do -50%", "GOOD"),
                ("Kontakt", "Zadzwoń lub napisz", "GOOD"),
                ("O nas", "Nasza historia", "LOW"),
            ],
            "CALLOUT": [
                ("Darmowa dostawa", None, "GOOD"),
                ("Raty 0%", None, "BEST"),
                ("Gwarancja 10 lat", None, "GOOD"),
                ("Zwrot 30 dni", None, "GOOD"),
            ],
            "STRUCTURED_SNIPPET": [
                ("Typy: Kanapy, Łóżka, Stoły, Krzesła", None, "GOOD"),
            ],
        },
        "Kanapy - Generic": {
            "SITELINK": [
                ("Kanapy skórzane", "Premium sofy", "GOOD"),
                ("Narożniki", "Duży wybór", "LOW"),
            ],
            "CALLOUT": [
                ("Skóra naturalna", None, "GOOD"),
                ("Transport gratis", None, "LEARNING"),
            ],
        },
        "Meble Biurowe": {
            "CALLOUT": [
                ("Ergonomiczne biurka", None, "GOOD"),
                ("Krzesła obrotowe", None, "LOW"),
            ],
        },
    }

    ext_asset_id = 8000
    for camp in campaigns:
        ext_config = extension_configs.get(camp.name, {})
        for ext_type, items in ext_config.items():
            for ext_name, ext_detail, ext_perf in items:
                ext_asset_id += 1
                base_clicks = RNG.randint(10, 500)
                base_impr = base_clicks * RNG.randint(8, 20)
                base_cost = base_clicks * RNG.uniform(0.3, 1.5)
                base_conv = round(max(0, base_clicks * RNG.uniform(0.01, 0.05)), 2)

                db.add(CampaignAsset(
                    campaign_id=camp.id,
                    google_asset_id=str(ext_asset_id),
                    asset_type=ext_type,
                    asset_name=ext_name,
                    asset_detail=ext_detail,
                    status="ENABLED",
                    performance_label=ext_perf,
                    source="ADVERTISER",
                    clicks=base_clicks,
                    impressions=base_impr,
                    cost_micros=int(base_cost * 1_000_000),
                    conversions=base_conv,
                    ctr=round(base_clicks / base_impr * 100, 2) if base_impr else 0,
                ))

    # -----------------------------------------------------------------------
    # Reports (seed sample reports so UI isn't empty)
    # -----------------------------------------------------------------------
    import json as _json
    today = date.today()

    seed_reports = []

    # Monthly report — previous month
    prev_month_start = date(today.year, today.month, 1) - timedelta(days=1)
    prev_month_start = date(prev_month_start.year, prev_month_start.month, 1)
    import calendar as _cal
    prev_month_end = date(prev_month_start.year, prev_month_start.month,
                          _cal.monthrange(prev_month_start.year, prev_month_start.month)[1])

    seed_reports.append(Report(
        client_id=client.id,
        report_type="monthly",
        period_label=f"{prev_month_start.year}-{prev_month_start.month:02d}",
        date_from=prev_month_start,
        date_to=prev_month_end,
        status="completed",
        report_data=_json.dumps({
            "kpis": {"clicks": 4823, "impressions": 98450, "cost_usd": 3245.60,
                     "conversions": 187, "ctr": 4.9, "roas": 5.2, "cpa": 17.35},
            "month_comparison": {"clicks_delta": 12.3, "cost_delta": -3.1,
                                 "conversions_delta": 8.7, "cpa_delta": -10.8},
            "top_campaigns": [
                {"name": "Search - Meble Biurowe", "cost_usd": 1240, "conversions": 68, "roas": 6.1},
                {"name": "PMax - Meble Ogrodowe", "cost_usd": 890, "conversions": 45, "roas": 4.8},
            ],
        }),
        ai_narrative=(
            "## Podsumowanie miesięczne\n\n"
            "Konto osiągnęło **187 konwersji** przy budżecie **3 245,60 zł**, "
            "co daje CPA na poziomie **17,35 zł** — spadek o 10,8% m/m.\n\n"
            "### Kluczowe obserwacje\n\n"
            "- **CTR wzrósł do 4,9%** (+0,3pp vs poprzedni miesiąc)\n"
            "- **ROAS utrzymuje się na 5,2** — powyżej targetu 4,0\n"
            "- Kampania *Search - Meble Biurowe* generuje najwyższy ROAS (6,1)\n"
            "- PMax stabilnie dostarcza 24% konwersji przy akceptowalnym CPA\n\n"
            "### Rekomendacje na następny miesiąc\n\n"
            "1. Zwiększ budżet kampanii Search - Meble Biurowe o 15% (IS lost budget = 22%)\n"
            "2. Dodaj 12 nowych negatywów ze search terms (WASTE segment)\n"
            "3. Przetestuj nowe RSA warianty w kampanii Meble Ogrodowe\n"
        ),
        model_name="claude-sonnet-4-6",
        input_tokens=12400,
        output_tokens=850,
        duration_ms=18500,
        created_at=datetime(prev_month_end.year, prev_month_end.month, prev_month_end.day, 9, 15),
        completed_at=datetime(prev_month_end.year, prev_month_end.month, prev_month_end.day, 9, 16),
    ))

    # Weekly report — last week
    week_start = today - timedelta(days=today.weekday() + 7)
    week_end = week_start + timedelta(days=6)
    seed_reports.append(Report(
        client_id=client.id,
        report_type="weekly",
        period_label=f"week-{week_start.isoformat()}",
        date_from=week_start,
        date_to=week_end,
        status="completed",
        report_data=_json.dumps({
            "kpis": {"clicks": 1205, "impressions": 24100, "cost_usd": 812.30,
                     "conversions": 48, "ctr": 5.0, "cpa": 16.92},
            "top_movers": [
                {"name": "Biurka regulowane", "change": "+34% konwersji"},
                {"name": "Krzesła gamingowe", "change": "-18% CTR"},
            ],
        }),
        ai_narrative=(
            "## Raport tygodniowy\n\n"
            "W minionym tygodniu konto wygenerowało **48 konwersji** "
            "przy wydatku **812,30 zł** (CPA = 16,92 zł).\n\n"
            "### Top zmiany\n\n"
            "- **Biurka regulowane**: +34% konwersji po dodaniu nowych RSA\n"
            "- **Krzesła gamingowe**: spadek CTR o 18% — wymaga analizy search terms\n\n"
            "### Do zrobienia\n\n"
            "- Przejrzyj search terms dla kampanii Krzesła (15 nowych WASTE)\n"
            "- Zwiększ bid na top 5 keywords z IS lost > 20%\n"
        ),
        model_name="claude-sonnet-4-6",
        input_tokens=8200,
        output_tokens=520,
        duration_ms=12300,
        created_at=datetime(week_end.year, week_end.month, week_end.day, 8, 30),
        completed_at=datetime(week_end.year, week_end.month, week_end.day, 8, 31),
    ))

    # Health report
    health_start = today - timedelta(days=29)
    seed_reports.append(Report(
        client_id=client.id,
        report_type="health",
        period_label=f"health-{today.isoformat()}",
        date_from=health_start,
        date_to=today,
        status="completed",
        report_data=_json.dumps({
            "health_score": 74,
            "structure": {"score": 82, "issues": ["2 ad groups z 1 RSA"]},
            "quality_scores": {"avg": 6.2, "below_5_count": 8},
            "conversion_health": {"active_actions": 3, "tracking_status": "healthy"},
        }),
        ai_narrative=(
            "## Audyt zdrowia konta\n\n"
            "**Ogólny wynik: 74/100**\n\n"
            "### Struktura konta (82/100)\n"
            "- 2 grupy reklam mają tylko 1 RSA — dodaj warianty\n"
            "- Ogólna struktura kampanii jest prawidłowa\n\n"
            "### Quality Score (6,2 avg)\n"
            "- 8 keywords z QS < 5 generuje 18% kosztów\n"
            "- Priorytet: popraw landing pages dla keywords z LP score = 'Below Average'\n\n"
            "### Śledzenie konwersji\n"
            "- 3 aktywne akcje konwersji — status healthy\n"
            "- Enhanced conversions włączone\n"
        ),
        model_name="claude-sonnet-4-6",
        input_tokens=15100,
        output_tokens=680,
        duration_ms=21000,
        created_at=datetime(today.year, today.month, today.day, 10, 0),
        completed_at=datetime(today.year, today.month, today.day, 10, 1),
    ))

    for r in seed_reports:
        db.add(r)

    db.flush()

    # -----------------------------------------------------------------------
    # DSA Campaign + Targets + Headlines + Overlapping Search Terms (C1, C2, C3)
    # -----------------------------------------------------------------------
    dsa_campaign = Campaign(
        client_id=client.id,
        google_campaign_id="1099",
        name="DSA - Meble Ogólne",
        status="ENABLED",
        campaign_type="SEARCH",
        campaign_subtype="SEARCH_DYNAMIC_ADS",
        budget_micros=int(200 * 1_000_000),
        budget_type="DAILY",
        bidding_strategy="TARGET_CPA",
        target_cpa_micros=int(25 * 1_000_000),
        primary_status="ELIGIBLE",
        start_date=date(2025, 6, 1),
        search_impression_share=_rand_is(RNG, 0.25, 0.65),
        search_top_impression_share=_rand_is(RNG, 0.15, 0.50),
        search_abs_top_impression_share=_rand_is(RNG, 0.08, 0.35),
        search_budget_lost_is=_rand_is(RNG, 0.02, 0.12),
        search_rank_lost_is=_rand_is(RNG, 0.05, 0.25),
    )
    db.add(dsa_campaign)
    db.flush()
    campaigns.append(dsa_campaign)

    # C1: DSA Targets (5 targets, mix of types)
    dsa_targets_data = [
        ("URL_CONTAINS", "/lozka", "ENABLED", 320, 8500, 480.0, 18.5),
        ("URL_CONTAINS", "/kanapy", "ENABLED", 210, 5600, 310.0, 11.2),
        ("CATEGORY", "Meble > Łóżka i materace", "ENABLED", 185, 4900, 275.0, 9.8),
        ("CATEGORY", "Meble > Sofy i narożniki", "ENABLED", 150, 3800, 220.0, 7.5),
        ("ALL_WEBPAGES", "*", "PAUSED", 45, 1200, 85.0, 1.2),
    ]
    dsa_target_objects = []
    for target_type, target_value, status, clicks, impr, cost, conv in dsa_targets_data:
        t = DsaTarget(
            client_id=client.id,
            campaign_id=dsa_campaign.id,
            target_type=target_type,
            target_value=target_value,
            status=status,
            clicks=clicks,
            impressions=impr,
            cost_micros=int(cost * 1_000_000),
            conversions=conv,
        )
        db.add(t)
        dsa_target_objects.append(t)
    db.flush()

    # C2: DSA Headlines (10 auto-generated headlines with metrics)
    dsa_headline_data = [
        ("łóżko drewniane 160x200", "Łóżka Drewniane - Darmowa Dostawa", "https://demo-meble.pl/lozka/drewniane"),
        ("kanapa narożna rozkładana", "Kanapy Narożne w Super Cenach", "https://demo-meble.pl/kanapy/narozne"),
        ("sofa do salonu skórzana", "Sofy Skórzane - Gwarancja 10 Lat", "https://demo-meble.pl/sofy/skorzane"),
        ("meble biurowe do domu", "Meble Biurowe - Ergonomiczne Biurka", "https://demo-meble.pl/biurka"),
        ("łóżko tapicerowane z pojemnikiem", "Łóżka Tapicerowane - Szeroki Wybór", "https://demo-meble.pl/lozka/tapicerowane"),
        ("stolik kawowy nowoczesny", "Nowoczesne Stoliki Kawowe", "https://demo-meble.pl/stoliki"),
        ("regał na książki drewniany", "Regały Drewniane - Raty 0%", "https://demo-meble.pl/regaly"),
        ("fotel obrotowy biurowy", "Fotele Biurowe - Ergonomia i Styl", "https://demo-meble.pl/fotele"),
        ("materac piankowy 140x200", "Materace Piankowe - Darmowy Zwrot", "https://demo-meble.pl/materace"),
        ("szafa przesuwna z lustrem", "Szafy Przesuwne - Montaż Gratis", "https://demo-meble.pl/szafy"),
    ]
    dsa_headline_objects = []
    for term, headline, url in dsa_headline_data:
        for day_offset in range(30):
            d = today - timedelta(days=day_offset)
            dow_factor = 0.7 if d.weekday() >= 5 else 1.0
            day_impr = max(1, int(RNG.gauss(80, 20) * dow_factor))
            day_ctr = RNG.uniform(0.03, 0.08)
            day_clicks = max(0, int(day_impr * day_ctr))
            day_cost = day_clicks * RNG.uniform(1.2, 3.5)
            day_conv = round(max(0, day_clicks * RNG.uniform(0.04, 0.12)), 2)

            h = DsaHeadline(
                client_id=client.id,
                campaign_id=dsa_campaign.id,
                search_term_text=term,
                generated_headline=headline,
                landing_page_url=url,
                clicks=day_clicks,
                impressions=day_impr,
                cost_micros=int(day_cost * 1_000_000),
                conversions=day_conv,
                date=d,
            )
            db.add(h)
            dsa_headline_objects.append(h)

        if (day_offset + 1) % 10 == 0:
            db.flush()

    db.flush()

    # C3: Overlapping search terms — add DSA search terms that overlap with existing ones
    # Some terms from "Branded Search" and "Łóżka - Generic" campaigns also appear in DSA
    overlapping_dsa_terms = [
        "łóżko drewniane",         # exists in Łóżka - Generic
        "łóżko drewniane 160x200", # exists in Łóżka - Generic
        "kanapa narożna",           # exists in Kanapy - Generic
        "sofa rozkładana",          # exists in Kanapy - Generic
        "biurko do domu",           # exists in Meble Biurowe
    ]
    for term in overlapping_dsa_terms:
        clicks = RNG.randint(15, 120)
        impr = RNG.randint(300, 3000)
        cost = RNG.uniform(20, 200)
        conv = round(RNG.uniform(0.5, 8), 2)
        conv_val = round(conv * RNG.uniform(80, 200), 2)
        db.add(SearchTerm(
            campaign_id=dsa_campaign.id,
            text=term,
            keyword_text=None,
            match_type=None,
            segment="OTHER",
            source="SEARCH",
            clicks=clicks,
            impressions=impr,
            cost_micros=int(cost * 1_000_000),
            conversions=conv,
            conversion_value_micros=int(conv_val * 1_000_000),
            ctr=round(clicks / impr * 100, 2) if impr else 0,
            date_from=today - timedelta(days=30),
            date_to=today,
        ))

    db.flush()

    # Daily metrics for DSA campaign (90 days)
    for day_offset in range(90):
        d = today - timedelta(days=day_offset)
        dow_factor = 0.75 if d.weekday() >= 5 else 1.0
        base_impr = max(10, int(RNG.gauss(800, 150) * dow_factor))
        base_ctr = RNG.uniform(0.035, 0.065)
        base_clicks = max(1, int(base_impr * base_ctr))
        base_cost = base_clicks * RNG.uniform(1.5, 3.0)
        base_conv = round(max(0, base_clicks * RNG.uniform(0.05, 0.10)), 2)
        base_cv = round(base_conv * RNG.uniform(100, 250), 2)
        db.add(MetricDaily(
            campaign_id=dsa_campaign.id,
            date=d,
            clicks=base_clicks,
            impressions=base_impr,
            cost_micros=int(base_cost * 1_000_000),
            conversions=base_conv,
            conversion_value_micros=int(base_cv * 1_000_000),
            ctr=round(base_clicks / base_impr * 100, 2) if base_impr else 0,
            avg_cpc_micros=int((base_cost / base_clicks) * 1_000_000) if base_clicks else 0,
        ))
        if (day_offset + 1) % 30 == 0:
            db.flush()

    db.flush()

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
    print("   - 90 days PMax channel breakdown (MetricSegmented + ad_network_type)")
    print(f"   - {len(asset_groups)} PMax asset groups + daily metrics + assets + signals")
    print("   - Campaign audience metrics (5 segments × 2 campaigns × 90 days)")
    print("   - Campaign extensions (sitelinks, callouts, snippets)")
    print(f"   - {len(seed_reports)} sample reports (monthly + weekly + health)")
    print(f"   - 1 DSA campaign + {len(dsa_target_objects)} targets + {len(dsa_headline_objects)} headline entries")
    print(f"   - {len(overlapping_dsa_terms)} overlapping DSA↔Search terms")


if __name__ == "__main__":
    seed_demo_data()
