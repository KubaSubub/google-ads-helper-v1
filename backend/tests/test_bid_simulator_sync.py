"""Tests for bid simulator sync.

Verified against live Google Ads API (v23, SDK 29.1.0) on 2026-04-18:
  - Resource: `ad_group_criterion_simulation` (not `_simulator`).
  - Fields: criterion_id, ad_group_id, type, start_date, end_date,
           cpc_bid_point_list.points[{cpc_bid_micros, clicks, impressions,
           cost_micros, biddable_conversions, biddable_conversions_value,
           top_slot_impressions}].

Google only computes keyword-level simulators for manual-CPC Search campaigns
with enough recent traffic; Smart Bidding accounts return 0 rows. Shopping
listing groups also return simulators here (type=LISTING_GROUP via
ad_group_criterion) but our SEARCH-only filter correctly skips those.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models import AdGroup, Campaign, Client, Keyword
from app.models.bid_simulator import BidSimulatorPoint
from app.services.google_ads import google_ads_service


def _build_mock_point(bid, clicks, impressions, cost_micros, conv, conv_val, top_slot=0):
    pt = MagicMock()
    pt.cpc_bid_micros = bid
    pt.clicks = clicks
    pt.impressions = impressions
    pt.cost_micros = cost_micros
    pt.biddable_conversions = conv
    pt.biddable_conversions_value = conv_val
    pt.top_slot_impressions = top_slot
    return pt


def _build_mock_row(criterion_id, ad_group_id, points, start="2026-04-09", end="2026-04-15"):
    sim = MagicMock()
    sim.criterion_id = criterion_id
    sim.ad_group_id = ad_group_id
    sim.type = "CPC_BID"
    sim.start_date = start
    sim.end_date = end
    sim.cpc_bid_point_list.points = points
    row = MagicMock()
    row.ad_group_criterion_simulation = sim
    return row


def _mk_fixture(db):
    client = Client(name="c", google_customer_id="5619914331"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="Search", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="191563900267", name="ag", status="ENABLED")
    db.add(ag); db.flush()
    kw = Keyword(
        ad_group_id=ag.id, google_keyword_id="293946777986",
        text="running shoes", match_type="EXACT", status="ENABLED",
        criterion_kind="POSITIVE", cost_micros=50_000_000,
    )
    db.add(kw); db.commit()
    return client, camp, ag, kw


def test_sync_parses_live_api_shape(db, monkeypatch):
    """Mocks the exact response shape observed on live API, verifies DB insert."""
    client, camp, ag, kw = _mk_fixture(db)

    # Match the exact criterion_id from the Keyword record so the lookup finds it.
    points = [
        _build_mock_point(1_500_000, 34, 4572, 15_360_000, 1.32, 2.40, 500),
        _build_mock_point(2_250_000, 52, 7844, 43_550_000, 1.66, 3.00, 800),
        _build_mock_point(2_700_000, 64, 9805, 65_370_000, 1.86, 3.40, 1000),
    ]
    mock_rows = [_build_mock_row("293946777986", 191563900267, points)]

    mock_ga = MagicMock()
    mock_ga.search.return_value = iter(mock_rows)
    mock_client = MagicMock()
    mock_client.get_service.return_value = mock_ga

    monkeypatch.setattr(google_ads_service, "client", mock_client)
    # Force is_connected to True via the property
    monkeypatch.setattr(type(google_ads_service), "is_connected", property(lambda self: True))

    n = google_ads_service.sync_bid_simulator_points(db, customer_id=client.google_customer_id)
    assert n == 3

    rows = db.query(BidSimulatorPoint).order_by(BidSimulatorPoint.point_index).all()
    assert len(rows) == 3
    assert rows[0].bid_micros == 1_500_000
    assert rows[0].forecasted_clicks == 34
    assert rows[0].forecasted_impressions == 4572
    assert rows[0].forecasted_cost_micros == 15_360_000
    assert rows[0].forecasted_conversions == pytest.approx(1.32)
    # biddable_conversions_value is a double, stored as micros
    assert rows[0].forecasted_conversions_value_micros == 2_400_000
    assert rows[0].forecasted_top_slot_impressions == 500
    assert rows[0].start_date == date(2026, 4, 9)
    assert rows[0].end_date == date(2026, 4, 15)


def test_sync_skips_criterion_not_in_local_db(db, monkeypatch):
    """API returns simulator for a criterion ID we don't track locally → skipped, not errored."""
    client, _camp, _ag, _kw = _mk_fixture(db)

    # Different criterion_id than our local keyword (e.g. Shopping listing group)
    orphan_rows = [_build_mock_row(
        "999999999",   # not in our DB
        191563900267,
        [_build_mock_point(1_000_000, 10, 100, 5_000_000, 0.5, 1.0)],
    )]

    mock_ga = MagicMock()
    mock_ga.search.return_value = iter(orphan_rows)
    mock_client = MagicMock()
    mock_client.get_service.return_value = mock_ga
    monkeypatch.setattr(google_ads_service, "client", mock_client)
    monkeypatch.setattr(type(google_ads_service), "is_connected", property(lambda self: True))

    n = google_ads_service.sync_bid_simulator_points(db, customer_id=client.google_customer_id)
    assert n == 0
    assert db.query(BidSimulatorPoint).count() == 0


def test_sync_returns_0_when_api_disconnected(db, monkeypatch):
    """Guard against running without a client."""
    client, _c, _ag, _kw = _mk_fixture(db)

    monkeypatch.setattr(type(google_ads_service), "is_connected", property(lambda self: False))
    n = google_ads_service.sync_bid_simulator_points(db, customer_id=client.google_customer_id)
    assert n == 0


def test_sync_handles_missing_point_list_gracefully(db, monkeypatch):
    """Simulator row with empty point list must not crash."""
    client, _c, _ag, kw = _mk_fixture(db)

    sim = MagicMock()
    sim.criterion_id = "293946777986"
    sim.ad_group_id = 191563900267
    sim.type = "CPC_BID"
    sim.start_date = "2026-04-09"
    sim.end_date = "2026-04-15"
    sim.cpc_bid_point_list = None   # edge case
    row = MagicMock()
    row.ad_group_criterion_simulation = sim

    mock_ga = MagicMock()
    mock_ga.search.return_value = iter([row])
    mock_client = MagicMock()
    mock_client.get_service.return_value = mock_ga
    monkeypatch.setattr(google_ads_service, "client", mock_client)
    monkeypatch.setattr(type(google_ads_service), "is_connected", property(lambda self: True))

    n = google_ads_service.sync_bid_simulator_points(db, customer_id=client.google_customer_id)
    assert n == 0


def test_sync_does_not_pick_up_paused_search_keywords(db, monkeypatch):
    """Only ENABLED Search keywords are eligible — PAUSED must not match."""
    client = Client(name="c", google_customer_id="5619914331"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="Search", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag1", name="ag", status="ENABLED")
    db.add(ag); db.flush()
    # PAUSED keyword
    kw = Keyword(
        ad_group_id=ag.id, google_keyword_id="293946777986",
        text="paused term", match_type="EXACT", status="PAUSED",
        criterion_kind="POSITIVE", cost_micros=50_000_000,
    )
    db.add(kw); db.commit()

    mock_ga = MagicMock()
    mock_ga.search.return_value = iter([_build_mock_row("293946777986", 1, [_build_mock_point(1_000_000, 10, 100, 5_000_000, 0.5, 1.0)])])
    mock_client = MagicMock()
    mock_client.get_service.return_value = mock_ga
    monkeypatch.setattr(google_ads_service, "client", mock_client)
    monkeypatch.setattr(type(google_ads_service), "is_connected", property(lambda self: True))

    n = google_ads_service.sync_bid_simulator_points(db, customer_id=client.google_customer_id)
    assert n == 0  # PAUSED keyword excluded from kw_lookup → skipped
