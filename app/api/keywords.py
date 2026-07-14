"""
API routes for keyword research (Module 4).

POST /api/keywords/research  -> runs the agent for given seed terms, returns a summary
GET  /api/keywords            -> lists researched keywords, filterable/sortable by opportunity
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.keyword_research_agent import KeywordResearchAgent
from app.core.database import get_db
from app.models.db_models import Platform
from app.models.schemas import KeywordOut, KeywordResearchRequest
from app.services.keyword_service import list_keywords

router = APIRouter()


@router.post("/research")
def trigger_research(
    request: KeywordResearchRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Run the Keyword Research Agent for the given seed terms. Synchronous —
    Module 9's scheduler can call this on a cadence with a standing seed list."""
    agent = KeywordResearchAgent()
    return agent.run(
        db,
        seed_terms=request.seed_terms,
        platforms=request.platforms,
        suggestions_per_seed=request.suggestions_per_seed,
    )


@router.get("", response_model=list[KeywordOut])
def get_keywords(
    platform: Platform | None = None,
    min_opportunity_score: float | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_keywords(
        db, platform=platform, min_opportunity_score=min_opportunity_score, limit=limit
    )
