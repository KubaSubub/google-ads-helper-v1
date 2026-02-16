"""CSV/Excel export endpoints."""

import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook

from app.database import get_db
from app.models import SearchTerm, MetricDaily, Campaign, AdGroup, Keyword

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/search-terms")
def export_search_terms(
    client_id: int = Query(...),
    format: str = Query("xlsx", description="xlsx or csv"),
    db: Session = Depends(get_db),
):
    """Export all search terms for a client as XLSX or CSV."""
    terms = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .order_by(SearchTerm.cost.desc())
        .all()
    )

    headers = ["Fraza", "Kliknięcia", "Wyświetlenia", "Koszt", "Konwersje", "CTR", "CPC", "Koszt/konw."]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for t in terms:
            cpc = t.cost / t.clicks if t.clicks else 0
            cpconv = t.cost / t.conversions if t.conversions > 0 else 0
            output.write(f'"{t.text}",{t.clicks},{t.impressions},{t.cost:.2f},{t.conversions:.1f},{t.ctr:.2f},{cpc:.2f},{cpconv:.2f}\n')
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
        cpc = t.cost / t.clicks if t.clicks else 0
        cpconv = t.cost / t.conversions if t.conversions > 0 else 0
        ws.append([t.text, t.clicks, t.impressions, round(t.cost, 2), round(t.conversions, 1), round(t.ctr, 2), round(cpc, 2), round(cpconv, 2)])

    # Auto-width columns
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
    cutoff = date.today() - timedelta(days=days)
    metrics = (
        db.query(MetricDaily)
        .filter(MetricDaily.campaign_id == campaign_id, MetricDaily.date >= cutoff)
        .order_by(MetricDaily.date)
        .all()
    )

    headers = ["Data", "Kliknięcia", "Wyświetlenia", "CTR", "Koszt", "Konwersje", "CPA", "ROAS", "Avg CPC"]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for m in metrics:
            output.write(f"{m.date},{m.clicks},{m.impressions},{m.ctr:.2f},{m.cost:.2f},{m.conversions:.1f},{m.cost_per_conversion:.2f},{m.roas:.2f},{m.avg_cpc:.2f}\n")
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
        ws.append([str(m.date), m.clicks, m.impressions, round(m.ctr, 2), round(m.cost, 2), round(m.conversions, 1), round(m.cost_per_conversion, 2), round(m.roas, 2), round(m.avg_cpc, 2)])

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
    keywords = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .order_by(Keyword.cost.desc())
        .all()
    )

    headers = ["Słowo kluczowe", "Dopasowanie", "Status", "Kliknięcia", "Wyświetlenia", "Koszt", "Konwersje", "CTR", "Avg CPC"]

    if format == "csv":
        output = io.StringIO()
        output.write(",".join(headers) + "\n")
        for k in keywords:
            output.write(f'"{k.text}",{k.match_type},{k.status},{k.clicks},{k.impressions},{k.cost:.2f},{k.conversions:.1f},{k.ctr:.2f},{k.avg_cpc:.2f}\n')
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
        ws.append([k.text, k.match_type, k.status, k.clicks, k.impressions, round(k.cost, 2), round(k.conversions, 1), round(k.ctr, 2), round(k.avg_cpc, 2)])

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
