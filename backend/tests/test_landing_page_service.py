"""Tests for landing page diagnostics service."""

import pytest

from app.models import AdGroup, Campaign, Client, Keyword
from app.services.landing_page_service import (
    _count_tracking_params,
    _normalise_url,
    landing_page_report,
)


def test_normalise_url_strips_query_and_trailing_slash():
    assert _normalise_url("https://example.com/path/") == "https://example.com/path"
    assert _normalise_url("https://example.com/path?utm=foo") == "https://example.com/path"
    assert _normalise_url("https://example.com/PATH") == "https://example.com/path"


def test_normalise_url_empty():
    assert _normalise_url("") == ""
    assert _normalise_url(None) == ""


def test_count_tracking_params():
    assert _count_tracking_params("https://ex.com?a={keyword}&b={campaign}") == 2
    assert _count_tracking_params("https://ex.com") == 0
    assert _count_tracking_params(None) == 0


def _mk(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(client_id=client.id, google_campaign_id="c1", name="camp",
                     status="ENABLED", campaign_type="SEARCH")
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag1", name="ag", status="ENABLED")
    db.add(ag); db.flush()
    return client, camp, ag


def _add_keyword(db, ag_id, text, final_url, clicks=50, impressions=1000,
                 cost_micros=50_000_000, conversions=1.0, lp_quality=None):
    db.add(Keyword(
        ad_group_id=ag_id, google_keyword_id=f"k-{text}", text=text,
        match_type="EXACT", status="ENABLED",
        cost_micros=cost_micros, clicks=clicks, impressions=impressions,
        conversions=conversions, final_url=final_url,
        historical_landing_page_quality=lp_quality,
    ))


def test_landing_page_report_aggregates_by_url(db):
    client, camp, ag = _mk(db)
    _add_keyword(db, ag.id, "kw1", "https://ex.com/page1", cost_micros=30_000_000)
    _add_keyword(db, ag.id, "kw2", "https://ex.com/page1?utm=x", cost_micros=70_000_000)
    db.commit()

    report = landing_page_report(db, client.id)
    assert len(report) == 1
    assert report[0]["keyword_count"] == 2
    assert report[0]["cost_usd"] == pytest.approx(100.0)


def test_flags_lp_below_average(db):
    client, camp, ag = _mk(db)
    # 3 out of 4 keywords have LP quality = 1 (BELOW_AVERAGE)
    _add_keyword(db, ag.id, "k1", "https://ex.com/slow", lp_quality=1)
    _add_keyword(db, ag.id, "k2", "https://ex.com/slow", lp_quality=1)
    _add_keyword(db, ag.id, "k3", "https://ex.com/slow", lp_quality=1)
    _add_keyword(db, ag.id, "k4", "https://ex.com/slow", lp_quality=3)
    db.commit()

    report = landing_page_report(db, client.id)
    assert any("LP_EXPERIENCE_BELOW_AVERAGE" in r["flags"] for r in report)


def test_flags_shared_across_many_ad_groups(db):
    client, camp, _ag = _mk(db)
    ag2 = AdGroup(campaign_id=camp.id, google_ad_group_id="ag2", name="ag2", status="ENABLED")
    ag3 = AdGroup(campaign_id=camp.id, google_ad_group_id="ag3", name="ag3", status="ENABLED")
    ag4 = AdGroup(campaign_id=camp.id, google_ad_group_id="ag4", name="ag4", status="ENABLED")
    db.add_all([ag2, ag3, ag4]); db.flush()

    for i, ag in enumerate([_ag, ag2, ag3, ag4]):
        _add_keyword(db, ag.id, f"kw{i}", "https://ex.com/same-lp")
    db.commit()

    report = landing_page_report(db, client.id)
    assert len(report) == 1
    assert any(f.startswith("SHARED_BY_") for f in report[0]["flags"])


def test_flags_tracking_template_complexity(db):
    client, camp, ag = _mk(db)
    _add_keyword(db, ag.id, "kw", "https://ex.com/page?a={keyword}&b={campaign}&c={adgroup}&d={matchtype}")
    db.commit()

    report = landing_page_report(db, client.id)
    assert any(f.startswith("TRACKING_TEMPLATE_") for f in report[0]["flags"])


def test_report_ordered_by_cost_desc(db):
    client, camp, ag = _mk(db)
    _add_keyword(db, ag.id, "cheap", "https://ex.com/cheap", cost_micros=10_000_000)
    _add_keyword(db, ag.id, "expensive", "https://ex.com/expensive", cost_micros=500_000_000)
    db.commit()

    report = landing_page_report(db, client.id)
    assert report[0]["url"] == "https://ex.com/expensive"
    assert report[1]["url"] == "https://ex.com/cheap"


def test_non_search_campaign_ignored(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(client_id=client.id, google_campaign_id="c1", name="camp",
                     status="ENABLED", campaign_type="PERFORMANCE_MAX")
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag", name="ag", status="ENABLED")
    db.add(ag); db.flush()
    _add_keyword(db, ag.id, "kw", "https://ex.com/page")
    db.commit()

    assert landing_page_report(db, client.id) == []
