"""
Seed the database with realistic demo data for development and testing.

Run with: python -m app.seed
"""

import random
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, init_db
from app.models import (
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily
)


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
    # Campaigns
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
        c = Campaign(
            client_id=client.id,
            google_campaign_id=str(1000 + i),
            name=name,
            status=status,
            campaign_type=ctype,
            budget_micros=int(budget * 1_000_000),  # Convert USD to micros
            budget_type="DAILY",
            bidding_strategy="TARGET_CPA" if ctype == "SEARCH" else "TARGET_ROAS",
            start_date=date(2025, 1, 1),
        )
        db.add(c)
        campaigns.append(c)
    db.flush()

    # -----------------------------------------------------------------------
    # Ad Groups & Keywords per campaign
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
    for campaign in campaigns:
        ag_configs = ad_groups_config.get(campaign.name, [])
        for j, (ag_name, keywords_list) in enumerate(ag_configs, start=1):
            ag = AdGroup(
                campaign_id=campaign.id,
                google_ad_group_id=str(2000 + campaign.id * 10 + j),
                name=ag_name,
                status="ENABLED",
                bid_micros=int(random.uniform(1.0, 5.0) * 1_000_000),  # Convert to micros
            )
            db.add(ag)
            db.flush()
            all_ad_groups.append(ag)

            for kw_text, match in keywords_list:
                kw = Keyword(
                    ad_group_id=ag.id,
                    google_keyword_id=str(random.randint(30000, 99999)),
                    text=kw_text,
                    match_type=match,
                    status="ENABLED",
                    clicks=random.randint(10, 500),
                    impressions=random.randint(200, 10000),
                    cost_micros=int(random.uniform(20, 800) * 1_000_000),  # Convert to micros
                    conversions=random.randint(0, 30),  # Integer, not float
                    ctr=int(random.uniform(1.0, 8.0) * 10_000),  # Store as micros (e.g., 50000 = 5%)
                    avg_cpc_micros=int(random.uniform(0.5, 5.0) * 1_000_000),  # Convert to micros
                    quality_score=random.choices(
                        range(1, 11),
                        weights=[2, 3, 5, 8, 12, 15, 18, 20, 12, 5],  # realistic distribution
                        k=1
                    )[0],
                )
                db.add(kw)

    db.flush()

    # -----------------------------------------------------------------------
    # Search Terms
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
        "jak wybrać łóżko do sypialni",  # Informational! Should be excluded
        "ikea łóżko malm",  # Competitor brand!
        "materac do łóżka",  # Loosely related, maybe exclude
    ]

    for ag in all_ad_groups:
        # Each ad group gets 5-12 random search terms
        terms = random.sample(search_terms_pool, min(len(search_terms_pool), random.randint(5, 12)))
        for term_text in terms:
            clicks = random.randint(1, 150)
            impressions = random.randint(clicks * 5, clicks * 30)
            cost = clicks * random.uniform(0.5, 4.0)
            conversions = int(random.uniform(0, clicks * 0.1))

            # Simplified keyword_text assignment
            campaign = db.get(Campaign, ag.campaign_id)
            campaign_name = campaign.name if campaign else ""
            keywords_for_campaign = ad_groups_config.get(campaign_name, [])
            if keywords_for_campaign:
                keyword_text = random.choice([kw for kw, _ in keywords_for_campaign[0][1]])
            else:
                keyword_text = "generic keyword"

            st = SearchTerm(
                ad_group_id=ag.id,
                text=term_text,
                keyword_text=keyword_text,
                clicks=clicks,
                impressions=impressions,
                cost_micros=int(cost * 1_000_000),  # Convert to micros
                conversions=conversions,
                ctr=int((clicks / impressions * 100) * 10_000 if impressions else 0),  # Store as micros
                conversion_rate=int((conversions / clicks * 100) * 10_000 if clicks else 0),  # Store as micros
                # cost_per_conversion removed - it's calculated, not stored
                date_from=date.today() - timedelta(days=30),
                date_to=date.today(),
            )
            db.add(st)

    # -----------------------------------------------------------------------
    # Ads (RSA)
    # -----------------------------------------------------------------------
    for ag in all_ad_groups:
        for ad_idx in range(random.randint(1, 3)):
            clicks = random.randint(50, 1000)
            impressions = random.randint(clicks * 8, clicks * 25)
            cost = clicks * random.uniform(0.8, 3.5)
            conversions = int(random.uniform(0, clicks * 0.08))

            ad = Ad(
                ad_group_id=ag.id,
                google_ad_id=str(random.randint(50000, 99999)),
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
                cost_micros=int(cost * 1_000_000),  # Convert to micros
                conversions=conversions,
                ctr=int((clicks / impressions * 100) * 10_000),  # Store as micros
            )
            db.add(ad)

    # -----------------------------------------------------------------------
    # Daily Metrics (last 90 days)
    # -----------------------------------------------------------------------
    for campaign in campaigns:
        if campaign.status == "PAUSED":
            continue

        base_clicks = random.randint(30, 200)
        base_cost = round(base_clicks * random.uniform(1.0, 3.0), 2)

        for day_offset in range(90):
            d = date.today() - timedelta(days=day_offset)
            # Add some daily variance and a slight upward trend
            trend_factor = 1 + (90 - day_offset) * 0.002  # Slight growth
            day_of_week_factor = 0.7 if d.weekday() >= 5 else 1.0  # Weekends lower

            clicks = max(1, int(base_clicks * trend_factor * day_of_week_factor * random.uniform(0.6, 1.4)))
            impressions = int(clicks * random.uniform(10, 25))
            cost = round(clicks * random.uniform(0.8, 3.5) * day_of_week_factor, 2)
            conversions = round(max(0, clicks * random.uniform(0.01, 0.08)), 1)

            dm = MetricDaily(
                campaign_id=campaign.id,
                date=d,
                clicks=clicks,
                impressions=impressions,
                ctr=round(clicks / impressions * 100 if impressions else 0, 2),
                conversions=conversions,
                conversion_rate=round(conversions / clicks * 100 if clicks else 0, 2),
                cost=cost,
                cost_per_conversion=round(cost / conversions if conversions > 0 else 0, 2),
                roas=round(conversions * 150 / cost if cost > 0 else 0, 2),  # Assuming avg order value ~150 PLN
                avg_cpc=round(cost / clicks if clicks else 0, 2),
            )
            db.add(dm)

    db.commit()
    db.close()

    print("✅ Demo data seeded successfully!")
    print("   - 1 client (Demo Meble)")
    print(f"   - {len(campaigns)} campaigns")
    print(f"   - {len(all_ad_groups)} ad groups")
    print("   - Keywords, search terms, ads, and 90 days of metrics")


if __name__ == "__main__":
    seed_demo_data()
