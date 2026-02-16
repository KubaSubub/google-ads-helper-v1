from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Any

from app.database import get_db
from app.services.google_ads import google_ads_service

router = APIRouter(tags=["Actions"])

class ActionRequest(BaseModel):
    action: str = Field(..., description="Action type: PAUSE_KEYWORD, PAUSE_AD, SET_KEYWORD_BID, ADD_KEYWORD")
    entity_id: int = Field(..., description="ID of the entity (keyword_id, ad_id, or ad_group_id)")
    params: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional parameters like new bid amount")

@router.post("/apply")
def apply_recommendation(
    request: ActionRequest,
    db: Session = Depends(get_db)
):
    """
    Execute a recommendation action.
    """
    result = google_ads_service.apply_action(
        db=db,
        action_type=request.action,
        entity_id=request.entity_id,
        params=request.params
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return result
