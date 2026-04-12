"""Shared factory helpers for test_scripts_* files.

Returns a full tree (client → campaigns → ad_groups → keywords → search_terms)
ready for dry_run/execute coverage. Import from test files, do not run as test.
"""

from datetime import date, timedelta

from app.models import (
    AdGroup,
    Campaign,
    Client,
    Keyword,
    NegativeKeyword,
    SearchTerm,
)


def build_basic_tree(db, *, client_name="Sushi Naka Naka"):
    """Seed one client, two Search campaigns, 2 ad groups, 2 keywords.

    Returns dict with references so tests can drive scripts deterministically.
    """
    client = Client(name=client_name, google_customer_id="111-111-1111")
    db.add(client)
    db.flush()

    camp_a = Campaign(
        client_id=client.id,
        google_campaign_id="c-a",
        name="Search A",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=50_000_000,
    )
    camp_b = Campaign(
        client_id=client.id,
        google_campaign_id="c-b",
        name="Search B",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=50_000_000,
    )
    db.add_all([camp_a, camp_b])
    db.flush()

    ag_a = AdGroup(
        campaign_id=camp_a.id,
        google_ad_group_id="ag-a",
        name="Group A",
        status="ENABLED",
    )
    ag_b = AdGroup(
        campaign_id=camp_b.id,
        google_ad_group_id="ag-b",
        name="Group B",
        status="ENABLED",
    )
    db.add_all([ag_a, ag_b])
    db.flush()

    kw_a = Keyword(
        ad_group_id=ag_a.id,
        google_keyword_id="kw-a",
        text="sushi wroclaw",
        match_type="PHRASE",
        status="ENABLED",
        criterion_kind="POSITIVE",
    )
    kw_b = Keyword(
        ad_group_id=ag_b.id,
        google_keyword_id="kw-b",
        text="dostawa sushi",
        match_type="PHRASE",
        status="ENABLED",
        criterion_kind="POSITIVE",
    )
    db.add_all([kw_a, kw_b])
    db.flush()

    db.commit()
    return {
        "client": client,
        "campaigns": {"a": camp_a, "b": camp_b},
        "ad_groups": {"a": ag_a, "b": ag_b},
        "keywords": {"a": kw_a, "b": kw_b},
    }


def add_search_term(
    db,
    *,
    tree,
    text,
    clicks=10,
    cost_pln=30.0,
    conversions=0.0,
    campaign_key="a",
    ad_group_key="a",
    days_ago_from=30,
    days_ago_to=1,
):
    camp = tree["campaigns"][campaign_key]
    ag = tree["ad_groups"].get(ad_group_key) if ad_group_key else None
    term = SearchTerm(
        ad_group_id=ag.id if ag else None,
        campaign_id=camp.id,
        text=text,
        clicks=clicks,
        impressions=max(clicks * 20, 1),
        cost_micros=int(cost_pln * 1_000_000),
        conversions=conversions,
        ctr=5.0,
        date_from=date.today() - timedelta(days=days_ago_from),
        date_to=date.today() - timedelta(days=days_ago_to),
    )
    db.add(term)
    db.flush()
    return term


def add_negative(db, *, client_id, campaign_id, text, match_type="PHRASE", ad_group_id=None):
    neg = NegativeKeyword(
        client_id=client_id,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        text=text,
        match_type=match_type,
        negative_scope="AD_GROUP" if ad_group_id else "CAMPAIGN",
        status="ENABLED",
        source="LOCAL_ACTION",
        criterion_kind="NEGATIVE",
    )
    db.add(neg)
    db.flush()
    return neg
