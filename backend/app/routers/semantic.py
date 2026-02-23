from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import SearchTerm
from app.services.semantic import SemanticService

router = APIRouter(
    prefix="/semantic",
    tags=["semantic"],
    responses={404: {"description": "Not found"}},
)

class ClusterMetric(BaseModel):
    cost: float
    conversions: float
    clicks: int
    impressions: int
    term_count: int

class ClusterItem(BaseModel):
    text: str
    cost: float
    conversions: float
    clicks: int
    impressions: int

class ClusterResponse(BaseModel):
    id: int
    name: str
    items: List[ClusterItem]
    metrics: ClusterMetric
    is_waste: bool

service = SemanticService()

@router.get("/clusters", response_model=List[ClusterResponse])
def get_semantic_clusters(
    client_id: int,
    days: int = 30,
    top_n: int = 1000,
    threshold: float = 1.0,
    db: Session = Depends(get_db)
):
    """
    Groups top search terms into semantic clusters.
    """
    from app.models import Campaign, AdGroup

    # Fetch top terms aggregated by text
    stmt = (
        db.query(
            SearchTerm.text,
            func.sum(SearchTerm.cost_micros).label("cost_micros"),
            func.sum(SearchTerm.conversions).label("conversions"),
            func.sum(SearchTerm.clicks).label("clicks"),
            func.sum(SearchTerm.impressions).label("impressions"),
        )
        .select_from(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .group_by(SearchTerm.text)
        .order_by(desc("cost_micros"))
        .limit(top_n)
    )
    
    rows = stmt.all()
    
    terms_data = [
        {
            "text": r.text,
            "cost": (r.cost_micros or 0) / 1_000_000,
            "conversions": r.conversions or 0.0,
            "clicks": r.clicks or 0,
            "impressions": r.impressions or 0
        }
        for r in rows
    ]
    
    if not terms_data:
        return []

    # Compute Clusters
    clusters = service.cluster_terms(terms_data, distance_threshold=threshold)
    
    return clusters
