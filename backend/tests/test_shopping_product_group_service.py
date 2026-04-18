"""Tests for Shopping product-group performance + feed heuristics."""

import pytest

from app.models import AdGroup, Campaign, Client
from app.models.product_group import ProductGroup
from app.services.shopping_product_group_service import product_group_report


def _mk_shopping(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="shop", status="ENABLED", campaign_type="SHOPPING",
    )
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag", name="ag", status="ENABLED")
    db.add(ag); db.flush()
    return client, camp, ag


def _add_pg(
    db, campaign_id, ad_group_id, criterion_id, *,
    partition_type="UNIT", parent_criterion_id=None,
    case_value=None, case_value_type=None,
    clicks=0, impressions=0, cost_micros=0, conversions=0.0,
    conv_value_micros=0, bid_micros=1_000_000,
):
    pg = ProductGroup(
        campaign_id=campaign_id, ad_group_id=ad_group_id,
        google_criterion_id=criterion_id,
        parent_criterion_id=parent_criterion_id,
        partition_type=partition_type,
        case_value=case_value, case_value_type=case_value_type,
        bid_micros=bid_micros,
        status="ENABLED",
        clicks=clicks, impressions=impressions, cost_micros=cost_micros,
        conversions=conversions, conversion_value_micros=conv_value_micros,
    )
    db.add(pg)
    return pg


def test_zero_impressions_with_bid_flagged_as_feed_issue(db):
    client, camp, ag = _mk_shopping(db)
    _add_pg(db, camp.id, ag.id, "c1", case_value="brand-a",
             impressions=0, clicks=0, bid_micros=500_000)
    db.commit()

    report = product_group_report(db, client.id)
    assert len(report) == 1
    assert "ZERO_IMPRESSIONS_WITH_BID" in report[0]["flags"]
    assert report[0]["severity"] == "HIGH"


def test_zero_conv_with_spend_flagged(db):
    client, camp, ag = _mk_shopping(db)
    _add_pg(db, camp.id, ag.id, "c1", case_value="brand-a",
             impressions=5000, clicks=150,
             cost_micros=100_000_000, conversions=0)
    db.commit()

    report = product_group_report(db, client.id)
    assert "ZERO_CONV_WITH_SPEND" in report[0]["flags"]
    assert report[0]["severity"] == "HIGH"  # $100 spend


def test_low_roas_vs_campaign_avg(db):
    client, camp, ag = _mk_shopping(db)
    # High-ROAS product (drives the average)
    _add_pg(db, camp.id, ag.id, "c1", case_value="winner",
             impressions=5000, clicks=200,
             cost_micros=50_000_000,   # $50
             conversions=10.0, conv_value_micros=500_000_000)  # ROAS 10
    # Low-ROAS product (< half of avg)
    _add_pg(db, camp.id, ag.id, "c2", case_value="loser",
             impressions=5000, clicks=200,
             cost_micros=50_000_000,   # $50
             conversions=2.0, conv_value_micros=50_000_000)   # ROAS 1
    db.commit()

    report = product_group_report(db, client.id)
    low = [r for r in report if r["case_value"] == "loser"]
    assert len(low) == 1
    assert "LOW_ROAS_VS_CAMPAIGN" in low[0]["flags"]


def test_high_roas_underserved(db):
    client, camp, ag = _mk_shopping(db)
    # Weaker baseline
    _add_pg(db, camp.id, ag.id, "c1", case_value="avg",
             impressions=5000, clicks=100, cost_micros=100_000_000,
             conversions=5.0, conv_value_micros=200_000_000)  # ROAS 2
    # High-ROAS item
    _add_pg(db, camp.id, ag.id, "c2", case_value="rockstar",
             impressions=1000, clicks=20, cost_micros=25_000_000,   # $25
             conversions=3.0, conv_value_micros=250_000_000)  # ROAS 10 — 5x avg
    db.commit()

    report = product_group_report(db, client.id)
    star = [r for r in report if r["case_value"] == "rockstar"]
    assert len(star) == 1
    assert "HIGH_ROAS_UNDERSERVED" in star[0]["flags"]


def test_subdivision_without_children_flagged(db):
    client, camp, ag = _mk_shopping(db)
    _add_pg(db, camp.id, ag.id, "root", case_value=None,
             partition_type="SUBDIVISION", parent_criterion_id=None)
    db.commit()

    report = product_group_report(db, client.id)
    assert any("SUBDIVISION_WITHOUT_CHILDREN" in r["flags"] for r in report)


def test_subdivision_with_child_not_flagged(db):
    client, camp, ag = _mk_shopping(db)
    _add_pg(db, camp.id, ag.id, "root",
             partition_type="SUBDIVISION", parent_criterion_id=None)
    _add_pg(db, camp.id, ag.id, "child-1",
             partition_type="UNIT", parent_criterion_id="root",
             case_value="brand-a", impressions=1000, clicks=20,
             cost_micros=10_000_000, conversions=1.0, conv_value_micros=50_000_000)
    db.commit()

    report = product_group_report(db, client.id)
    # Only UNIT is fine here (neither high nor low severity)
    subs = [r for r in report if r["partition_type"] == "SUBDIVISION"]
    assert subs == []


def test_non_shopping_campaign_skipped(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="search", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag", name="ag", status="ENABLED")
    db.add(ag); db.flush()

    _add_pg(db, camp.id, ag.id, "c1", case_value="brand",
             impressions=0, clicks=0, bid_micros=1_000_000)
    db.commit()

    assert product_group_report(db, client.id) == []


def test_findings_sorted_by_severity_then_cost(db):
    client, camp, ag = _mk_shopping(db)
    # Low-severity orphan subdivision
    _add_pg(db, camp.id, ag.id, "orphan",
             partition_type="SUBDIVISION", parent_criterion_id=None)
    # High-severity zero-impression with bid
    _add_pg(db, camp.id, ag.id, "high", case_value="brand-x",
             partition_type="UNIT", impressions=0, bid_micros=500_000)
    db.commit()

    report = product_group_report(db, client.id)
    # HIGH severity must come first
    assert report[0]["severity"] == "HIGH"
