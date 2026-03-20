"""Tests for reports router — list and get report endpoints."""

import json
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.client import Client
from app.models.report import Report


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_reports(db):
    """Seed two clients with reports for isolation testing."""
    client_a = Client(name="Report Client A", google_customer_id="6660001110")
    client_b = Client(name="Report Client B", google_customer_id="6660002220")
    db.add_all([client_a, client_b])
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    report_a1 = Report(
        client_id=client_a.id,
        report_type="monthly",
        period_label="2026-02",
        date_from=date(2026, 2, 1),
        date_to=date(2026, 2, 28),
        status="completed",
        report_data=json.dumps({"campaigns_detail": {"total": 5}}),
        ai_narrative="Raport miesiczny za luty 2026.",
        created_at=now,
        completed_at=now,
    )
    report_a2 = Report(
        client_id=client_a.id,
        report_type="monthly",
        period_label="2026-01",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        status="completed",
        report_data=json.dumps({"campaigns_detail": {"total": 3}}),
        ai_narrative="Raport za styczen.",
        created_at=now,
        completed_at=now,
    )
    report_b1 = Report(
        client_id=client_b.id,
        report_type="monthly",
        period_label="2026-02",
        date_from=date(2026, 2, 1),
        date_to=date(2026, 2, 28),
        status="completed",
        report_data=json.dumps({"campaigns_detail": {"total": 8}}),
        ai_narrative="Raport klienta B.",
        created_at=now,
        completed_at=now,
    )

    db.add_all([report_a1, report_a2, report_b1])
    db.commit()
    return client_a, client_b, report_a1, report_a2, report_b1


# ---------------------------------------------------------------------------
# List reports
# ---------------------------------------------------------------------------


class TestListReports:
    def test_returns_reports_for_client(self, api_client, db):
        client_a, _, _, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/?client_id={client_a.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2
        assert len(data["reports"]) == 2

    def test_does_not_return_other_clients_reports(self, api_client, db):
        client_a, client_b, _, _, _ = _seed_reports(db)

        resp_a = api_client.get(f"/api/v1/reports/?client_id={client_a.id}")
        resp_b = api_client.get(f"/api/v1/reports/?client_id={client_b.id}")

        assert resp_a.json()["total"] == 2
        assert resp_b.json()["total"] == 1

    def test_empty_result_for_nonexistent_client(self, api_client, db):
        resp = api_client.get("/api/v1/reports/?client_id=99999")
        data = resp.json()
        assert data["total"] == 0
        assert data["reports"] == []

    def test_limit_and_offset(self, api_client, db):
        client_a, _, _, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/?client_id={client_a.id}&limit=1&offset=0")
        data = resp.json()
        assert len(data["reports"]) == 1
        assert data["total"] == 2

        resp2 = api_client.get(f"/api/v1/reports/?client_id={client_a.id}&limit=1&offset=1")
        data2 = resp2.json()
        assert len(data2["reports"]) == 1
        # Different report than first page
        assert data2["reports"][0]["id"] != data["reports"][0]["id"]

    def test_report_fields_present(self, api_client, db):
        client_a, _, _, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/?client_id={client_a.id}")
        report = resp.json()["reports"][0]

        assert "id" in report
        assert "report_type" in report
        assert "period_label" in report
        assert "status" in report
        assert "created_at" in report


# ---------------------------------------------------------------------------
# Get report
# ---------------------------------------------------------------------------


class TestGetReport:
    def test_returns_full_report(self, api_client, db):
        client_a, _, report_a1, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/{report_a1.id}?client_id={client_a.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["id"] == report_a1.id
        assert data["client_id"] == client_a.id
        assert data["report_type"] == "monthly"
        assert data["ai_narrative"] == "Raport miesiczny za luty 2026."
        assert data["report_data"] is not None
        assert data["report_data"]["campaigns_detail"]["total"] == 5

    def test_client_id_isolation(self, api_client, db):
        """Report from client A cannot be fetched with client B's ID."""
        client_a, client_b, report_a1, _, _ = _seed_reports(db)

        # Correct client — should work
        resp_ok = api_client.get(f"/api/v1/reports/{report_a1.id}?client_id={client_a.id}")
        assert resp_ok.status_code == 200

        # Wrong client — should 404
        resp_fail = api_client.get(f"/api/v1/reports/{report_a1.id}?client_id={client_b.id}")
        assert resp_fail.status_code == 404

    def test_nonexistent_report_404(self, api_client, db):
        client_a, _, _, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/99999?client_id={client_a.id}")
        assert resp.status_code == 404

    def test_report_data_parsed_as_dict(self, api_client, db):
        """report_data should be returned as parsed JSON dict, not raw string."""
        client_a, _, report_a1, _, _ = _seed_reports(db)

        resp = api_client.get(f"/api/v1/reports/{report_a1.id}?client_id={client_a.id}")
        data = resp.json()

        assert isinstance(data["report_data"], dict)

    def test_report_with_no_narrative(self, api_client, db):
        """Report without AI narrative should still return successfully."""
        client = Client(name="No Narrative", google_customer_id="6660003330")
        db.add(client)
        db.flush()

        report = Report(
            client_id=client.id,
            report_type="monthly",
            period_label="2026-03",
            status="completed",
            report_data=json.dumps({"summary": "ok"}),
            ai_narrative=None,
        )
        db.add(report)
        db.commit()

        resp = api_client.get(f"/api/v1/reports/{report.id}?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json()["ai_narrative"] is None


# ---------------------------------------------------------------------------
# Weekly / Health report type storage
# ---------------------------------------------------------------------------


class TestReportTypes:
    def test_weekly_report_stored(self, api_client, db):
        """Weekly report can be stored and retrieved."""
        client = Client(name="Weekly Test", google_customer_id="6660004440")
        db.add(client)
        db.flush()

        report = Report(
            client_id=client.id,
            report_type="weekly",
            period_label="week-2026-03-14",
            date_from=date(2026, 3, 14),
            date_to=date(2026, 3, 20),
            status="completed",
            report_data=json.dumps({"kpis": {"clicks": 100}}),
            ai_narrative="Raport tygodniowy.",
        )
        db.add(report)
        db.commit()

        resp = api_client.get(f"/api/v1/reports/{report.id}?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "weekly"
        assert "week-" in data["period_label"]

    def test_health_report_stored(self, api_client, db):
        """Health report can be stored and retrieved."""
        client = Client(name="Health Test", google_customer_id="6660005550")
        db.add(client)
        db.flush()

        report = Report(
            client_id=client.id,
            report_type="health",
            period_label="health-2026-03-20",
            date_from=date(2026, 2, 19),
            date_to=date(2026, 3, 20),
            status="completed",
            report_data=json.dumps({"health": {"score": 78}}),
            ai_narrative="Raport zdrowia konta.",
        )
        db.add(report)
        db.commit()

        resp = api_client.get(f"/api/v1/reports/{report.id}?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "health"
        assert "health-" in data["period_label"]

    def test_list_filters_by_report_type_implicitly(self, api_client, db):
        """All report types appear in list for a client."""
        client = Client(name="Multi Type", google_customer_id="6660006660")
        db.add(client)
        db.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for rt in ["monthly", "weekly", "health"]:
            db.add(Report(
                client_id=client.id,
                report_type=rt,
                period_label=f"{rt}-test",
                status="completed",
                created_at=now,
            ))
        db.commit()

        resp = api_client.get(f"/api/v1/reports/?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        types = {r["report_type"] for r in data["reports"]}
        assert types == {"monthly", "weekly", "health"}
