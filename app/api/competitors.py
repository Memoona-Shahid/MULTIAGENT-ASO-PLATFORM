"""
API routes for competitor analysis (Module 5).

POST /api/competitors/analyze       -> runs the agent for specific apps
GET  /api/competitors               -> lists tracked competitors
GET  /api/competitors/{id}/reviews  -> lists sampled reviews for one competitor
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent
from app.core.database import get_db
from app.models.db_models import Platform
from app.models.schemas import CompetitorAnalysisRequest, CompetitorOut, ReviewOut
from app.services.competitor_service import get_competitor, list_competitor_reviews, list_competitors

router = APIRouter()


@router.post("/analyze")
def trigger_analysis(
    request: CompetitorAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Run the Competitor Analysis Agent for the requested store apps."""
    agent = CompetitorAnalysisAgent()
    targets = [target.model_dump() for target in request.targets]
    return agent.run(db, targets=targets, reviews_per_app=request.reviews_per_app)


@router.get("", response_model=list[CompetitorOut])
def get_competitors(
    platform: Platform | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_competitors(db, platform=platform, category=category, limit=limit)


@router.get("/{competitor_id}/reviews", response_model=list[ReviewOut])
def get_reviews(
    competitor_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    if get_competitor(db, competitor_id) is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return list_competitor_reviews(db, competitor_id=competitor_id, limit=limit)
