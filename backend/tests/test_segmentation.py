"""Tests for search term segmentation logic."""

import re
from datetime import date, timedelta
from app.models import Client, Campaign, AdGroup, SearchTerm
from app.services.search_terms_service import SearchTermsService
from app.utils.constants import IRRELEVANT_KEYWORDS

# Pre-compiled patterns, same as the service builds them
_IRRELEVANT_PATTERNS = [
    re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
    for kw in IRRELEVANT_KEYWORDS
]


def _setup_data(db, terms_data: list[dict]):
    """Helper: create client + campaign + ad_group + search terms."""
    client = Client(name="Test", google_customer_id="1")
    db.add(client)
    db.commit()

    campaign = Campaign(
        client_id=client.id, name="Camp", google_campaign_id="c1", status="ENABLED"
    )
    db.add(campaign)
    db.commit()

    ag = AdGroup(
        campaign_id=campaign.id, name="AG", google_ad_group_id="ag1", status="ENABLED"
    )
    db.add(ag)
    db.commit()

    for td in terms_data:
        st = SearchTerm(
            ad_group_id=ag.id,
            text=td["text"],
            clicks=td.get("clicks", 0),
            impressions=td.get("impressions", 0),
            cost_micros=td.get("cost_micros", 0),
            conversions=td.get("conversions", 0),
            ctr=td.get("ctr", 0),
            conversion_rate=td.get("conversion_rate", 0),
            date_from=date.today() - timedelta(days=30),
            date_to=date.today(),
        )
        db.add(st)
    db.commit()

    return client


def test_irrelevant_segment(db):
    """Terms containing IRRELEVANT_KEYWORDS should be classified as IRRELEVANT."""
    client = _setup_data(db, [
        {"text": "darmowe kursy google ads", "clicks": 10, "impressions": 200},
        {"text": "tutorial google ads", "clicks": 5, "impressions": 100},
    ])

    service = SearchTermsService(db)
    result = service._classify(
        db.query(SearchTerm).filter(SearchTerm.text == "darmowe kursy google ads").first(),
        {},
        _IRRELEVANT_PATTERNS,
    )
    assert result == "IRRELEVANT"

    result2 = service._classify(
        db.query(SearchTerm).filter(SearchTerm.text == "tutorial google ads").first(),
        {},
        _IRRELEVANT_PATTERNS,
    )
    assert result2 == "IRRELEVANT"


def test_high_performer_segment(db):
    """Terms with conv >= 3 and CVR > campaign avg should be HIGH_PERFORMER."""
    client = _setup_data(db, [
        {"text": "agency google ads", "clicks": 50, "conversions": 5, "impressions": 500},
    ])

    service = SearchTermsService(db)
    # Campaign avg CVR = 0.05 (5%), term CVR = 5/50 = 0.10 (10%) > 0.05
    campaign_cvrs = {1: 0.05}
    result = service._classify(
        db.query(SearchTerm).first(),
        campaign_cvrs,
        _IRRELEVANT_PATTERNS,
    )
    assert result == "HIGH_PERFORMER"


def test_waste_segment(db):
    """Terms with clicks >= 5, conv = 0, CTR < 1% should be WASTE."""
    client = _setup_data(db, [
        {
            "text": "random query",
            "clicks": 10,
            "conversions": 0,
            "impressions": 5000,
            "ctr": 2000,  # 0.2% in micros (2000 / 1_000_000 = 0.000002 as decimal < 0.01)
        },
    ])

    service = SearchTermsService(db)
    result = service._classify(db.query(SearchTerm).first(), {}, _IRRELEVANT_PATTERNS)
    assert result == "WASTE"


def test_other_segment_default(db):
    """Terms that don't match any rule should be OTHER."""
    client = _setup_data(db, [
        {"text": "normal query", "clicks": 2, "conversions": 0, "impressions": 50},
    ])

    service = SearchTermsService(db)
    result = service._classify(db.query(SearchTerm).first(), {}, _IRRELEVANT_PATTERNS)
    assert result == "OTHER"


def test_irrelevant_takes_priority(db):
    """IRRELEVANT should win even if term also qualifies as HIGH_PERFORMER."""
    client = _setup_data(db, [
        {"text": "darmowe narzedzia seo", "clicks": 100, "conversions": 5, "impressions": 1000},
    ])

    service = SearchTermsService(db)
    campaign_cvrs = {1: 0.01}
    result = service._classify(db.query(SearchTerm).first(), campaign_cvrs, _IRRELEVANT_PATTERNS)
    assert result == "IRRELEVANT"  # "darmowe" is an irrelevant keyword
