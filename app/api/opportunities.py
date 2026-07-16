"""
API routes for Market Opportunity synthesis (Module 7).

POST /api/opportunities/synthesize  -> runs the Market Opportunity Agent
GET  /api/opportunities             -> lists scored opportunities
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.market_opportunity_agent import MarketOpportunityAgent
from app.core.database import get_db
from app.models.schemas import (
    MarketOpportunityOut,
    MarketOpportunitySynthesisRequest,
)
from app.services.market_opportunity_service import list_market_opportunities

router = APIRouter()


@router.post("/synthesize")
def synthesize_opportunities(
    request: MarketOpportunitySynthesisRequest,
    db: Session = Depends(get_db),
) -> dict:
    agent = MarketOpportunityAgent()
    return agent.run(
        db,
        min_score=request.min_score,
        min_keyword_opportunity=request.min_keyword_opportunity,
        per_source_limit=request.per_source_limit,
    )


@router.get("", response_model=list[MarketOpportunityOut])
def get_opportunities(
    category: str | None = None,
    min_opportunity_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_market_opportunities(
        db,
        category=category,
        min_opportunity_score=min_opportunity_score,
        limit=limit,
    )
