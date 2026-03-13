"""CSV/Excel export endpoints."""

import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdGroup, Campaign, Client, Keyword, MetricDaily, SearchTerm
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

    def _row(term):
        cost_usd = micros_to_currency(term.cost_micros)
        cpc = cost_usd / term.clicks if term.clicks else 0
        cpconv = cost_usd / term.conversions if (term.conversions or 0) > 0 else 0
        ctr_pct = round((term.ctr or 0) / 10_000, 2)
        return [term.text, term.clicks or 0, term.impressions or 0, cost_usd, term.conversions or 0, ctr_pct, round(cpc, 2), round(cpconv, 2)]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for term in terms:
            row = _row(term)
            output.write(f'"{row[0]}",{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7]}\n')
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=search_terms.csv"},
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Search Terms"
    ws.append(headers)
    for term in terms:
        ws.append(_row(term))

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
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

    def _row(metric):
        cost_usd = micros_to_currency(metric.cost_micros)
        cpa = cost_usd / metric.conversions if (metric.conversions or 0) > 0 else 0
        ctr_pct = round((metric.ctr or 0) / 10_000, 2)
        avg_cpc_usd = micros_to_currency(metric.avg_cpc_micros)
        return [str(metric.date), metric.clicks or 0, metric.impressions or 0, ctr_pct, cost_usd, metric.conversions or 0, round(cpa, 2), round(metric.roas or 0, 2), avg_cpc_usd]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for metric in metrics:
            row = _row(metric)
            output.write(",".join(str(value) for value in row) + "\n")
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
    for metric in metrics:
        ws.append(_row(metric))

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
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
    campaign_id: int = Query(None),
    include_removed: bool = Query(False),
    format: str = Query("xlsx"),
    db: Session = Depends(get_db),
):
    """Export keywords for a client as XLSX or CSV."""
    _validate_client(db, client_id)
    if campaign_id is not None:
        _validate_campaign(db, campaign_id)

    keywords = (
        db.query(Keyword, Campaign.name.label("campaign_name"), AdGroup.name.label("ad_group_name"))
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if campaign_id is not None:
        keywords = keywords.filter(Campaign.id == campaign_id)
    if not include_removed:
        keywords = keywords.filter(Keyword.status.in_(("ENABLED", "PAUSED")))
    keywords = keywords.order_by(Keyword.cost_micros.desc()).all()

    headers = ["Kampania", "Grupa reklam", "Slowo kluczowe", "Dopasowanie", "Status", "Klikniecia", "Wyswietlenia", "Koszt (USD)", "Konwersje", "CTR %", "Avg CPC (USD)"]

    def _row(keyword, campaign_name, ad_group_name):
        cost_usd = micros_to_currency(keyword.cost_micros)
        ctr_pct = round((keyword.ctr or 0) / 10_000, 2)
        avg_cpc_usd = micros_to_currency(keyword.avg_cpc_micros)
        return [campaign_name, ad_group_name, keyword.text, keyword.match_type, keyword.status, keyword.clicks or 0, keyword.impressions or 0, cost_usd, keyword.conversions or 0, ctr_pct, avg_cpc_usd]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for keyword, campaign_name, ad_group_name in keywords:
            row = _row(keyword, campaign_name, ad_group_name)
            output.write(",".join(f'"{value}"' if isinstance(value, str) else str(value) for value in row) + "\n")
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
    for keyword, campaign_name, ad_group_name in keywords:
        ws.append(_row(keyword, campaign_name, ad_group_name))

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
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

    def _row(result):
        return [
            result.get("priority", ""),
            result.get("type", ""),
            result.get("entity_name", ""),
            result.get("campaign_name", ""),
            result.get("reason", ""),
            result.get("current_value", ""),
            result.get("recommended_action", ""),
            result.get("estimated_impact", ""),
        ]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for result in results:
            row = _row(result)
            output.write(",".join(f'"{value}"' for value in row) + "\n")
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
    for result in results:
        ws.append(_row(result))

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=recommendations.xlsx"},
    )
