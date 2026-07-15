"""
API routes for Reviews Intelligence (Module 6).

POST /api/reviews/analyze  -> pulls/analyzes recent reviews for tracked competitors
GET  /api/reviews          -> lists analyzed reviews with useful filters
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.reviews_intelligence_agent import ReviewsIntelligenceAgent
from app.core.database import get_db
from app.models.db_models import Platform
from app.models.schemas import ReviewIntelligenceRequest, ReviewOut
from app.services.review_service import list_reviews

router = APIRouter()


@router.post("/analyze")
def trigger_analysis(
    request: ReviewIntelligenceRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Run the Reviews Intelligence Agent synchronously for tracked competitors."""
    agent = ReviewsIntelligenceAgent()
    return agent.run(
        db,
        competitor_ids=request.competitor_ids,
        platform=request.platform,
        reviews_per_competitor=request.reviews_per_competitor,
        tracked_competitor_limit=request.tracked_competitor_limit,
    )


@router.get("", response_model=list[ReviewOut])
def get_reviews(
    competitor_id: int | None = None,
    platform: Platform | None = None,
    sentiment: str | None = Query(default=None, pattern="^(positive|neutral|negative)$"),
    mentions_bug: bool | None = None,
    mentions_feature_request: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_reviews(
        db,
        competitor_id=competitor_id,
        platform=platform,
        sentiment=sentiment,
        mentions_bug=mentions_bug,
        mentions_feature_request=mentions_feature_request,
        limit=limit,
    )
