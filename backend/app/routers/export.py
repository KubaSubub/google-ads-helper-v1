"""CSV/Excel export endpoints."""

import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook

from app.database import get_db
from app.models import SearchTerm, MetricDaily, Campaign, AdGroup, Keyword, Client
from app.services.recommendations import recommendations_engine
from app.utils.formatters import micros_to_currency

router = APIRouter(prefix="/export", tags=["Export"])


def _validate_client(db: Session, client_id: int) -> Client:
    """Validate client exists, raise 404 if not."""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return client


def _validate_campaign(db: Session, campaign_id: int) -> Campaign:
    """Validate campaign exists, raise 404 if not."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return campaign


@router.get("/search-terms")
def export_search_terms(
    client_id: int = Query(...),
    format: str = Query("xlsx", description="xlsx or csv"),
    db: Session = Depends(get_db),
):
    """Export all search terms for a client as XLSX or CSV."""
    _validate_client(db, client_id)

    terms = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .order_by(SearchTerm.cost_micros.desc())
        .all()
    )

    headers = ["Fraza", "Klikniecia", "Wyswietlenia", "Koszt (USD)", "Konwersje", "CTR %", "CPC (USD)", "Koszt/konw. (USD)"]

    def _row(t):
        cost_usd = micros_to_currency(t.cost_micros)
        cpc = cost_usd / t.clicks if t.clicks else 0
        cpconv = cost_usd / t.conversions if (t.conversions or 0) > 0 else 0
        ctr_pct = round((t.ctr or 0) / 10_000, 2)
        return [t.text, t.clicks or 0, t.impressions or 0, cost_usd, t.conversions or 0, ctr_pct, round(cpc, 2), round(cpconv, 2)]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for t in terms:
            row = _row(t)
            output.write(f'"{row[0]}",{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7]}\n')
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=search_terms.csv"},
        )

    # XLSX
    wb = Workbook()
    ws = wb.active
    ws.title = "Search Terms"
    ws.append(headers)
    for t in terms:
        ws.append(_row(t))

    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=search_terms.xlsx"},
    )


@router.get("/metrics")
def export_metrics(
    campaign_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Export daily metrics for a campaign as XLSX or CSV."""
    _validate_campaign(db, campaign_id)

    cutoff = date.today() - timedelta(days=days)
    metrics = (
        db.query(MetricDaily)
        .filter(MetricDaily.campaign_id == campaign_id, MetricDaily.date >= cutoff)
        .order_by(MetricDaily.date)
        .all()
    )

    headers = ["Data", "Klikniecia", "Wyswietlenia", "CTR %", "Koszt (USD)", "Konwersje", "CPA (USD)", "ROAS", "Avg CPC (USD)"]

    def _row(m):
        cost_usd = micros_to_currency(m.cost_micros)
        cpa = cost_usd / m.conversions if (m.conversions or 0) > 0 else 0
        ctr_pct = round((m.ctr or 0) / 10_000, 2)
        avg_cpc_usd = micros_to_currency(m.avg_cpc_micros)
        return [str(m.date), m.clicks or 0, m.impressions or 0, ctr_pct, cost_usd, m.conversions or 0, round(cpa, 2), round(m.roas or 0, 2), avg_cpc_usd]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for m in metrics:
            row = _row(m)
            output.write(",".join(str(v) for v in row) + "\n")
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=metrics_campaign_{campaign_id}.csv"},
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Metrics"
    ws.append(headers)
    for m in metrics:
        ws.append(_row(m))

    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=metrics_campaign_{campaign_id}.xlsx"},
    )


@router.get("/keywords")
def export_keywords(
    client_id: int = Query(...),
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Export all keywords for a client as XLSX or CSV."""
    _validate_client(db, client_id)

    keywords = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .order_by(Keyword.cost_micros.desc())
        .all()
    )

    headers = ["Slowo kluczowe", "Dopasowanie", "Status", "Klikniecia", "Wyswietlenia", "Koszt (USD)", "Konwersje", "CTR %", "Avg CPC (USD)"]

    def _row(k):
        cost_usd = micros_to_currency(k.cost_micros)
        ctr_pct = round((k.ctr or 0) / 10_000, 2)
        avg_cpc_usd = micros_to_currency(k.avg_cpc_micros)
        return [k.text, k.match_type, k.status, k.clicks or 0, k.impressions or 0, cost_usd, k.conversions or 0, ctr_pct, avg_cpc_usd]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for k in keywords:
            row = _row(k)
            output.write(f'"{row[0]}",{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7]},{row[8]}\n')
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=keywords.csv"},
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Keywords"
    ws.append(headers)
    for k in keywords:
        ws.append(_row(k))

    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=keywords.xlsx"},
    )


@router.get("/recommendations")
def export_recommendations(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Export recommendations for a client as XLSX or CSV."""
    _validate_client(db, client_id)

    results = recommendations_engine.generate_all(db, client_id, days)

    headers = ["Priorytet", "Typ", "Encja", "Kampania", "Powod", "Obecna wartosc", "Rekomendacja", "Szacowany wplyw"]

    def _row(r):
        return [
            r.get("priority", ""),
            r.get("type", ""),
            r.get("entity_name", ""),
            r.get("campaign_name", ""),
            r.get("reason", ""),
            r.get("current_value", ""),
            r.get("recommended_action", ""),
            r.get("estimated_impact", ""),
        ]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for r in results:
            row = _row(r)
            output.write(",".join(f'"{v}"' for v in row) + "\n")
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=recommendations.csv"},
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Recommendations"
    ws.append(headers)
    for r in results:
        ws.append(_row(r))

    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=recommendations.xlsx"},
    )
