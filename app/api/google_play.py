"""
API routes for Google Play trending data (Module 3).

POST /api/google-play/research  -> runs the agent synchronously, returns a summary
GET  /api/google-play/trending  -> lists the most recent snapshot, with filters
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.google_play_research_agent import GooglePlayResearchAgent
from app.core.database import get_db
from app.models.db_models import ChartType, Platform
from app.models.schemas import TrendingAppOut
from app.services.trending_app_service import list_trending_apps

router = APIRouter()


@router.post("/research")
def trigger_research(
    limit: int = Query(default=100, ge=1, le=200),
    fetch_details: bool = Query(
        default=False,
        description="Also fetch per-app rating counts (one request per app, slower).",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Run the Google Play Research Agent now. Synchronous — Module 9's
    scheduler will be what calls this automatically on a daily cadence."""
    agent = GooglePlayResearchAgent()
    return agent.run(db, limit=limit, fetch_details=fetch_details)


@router.get("/trending", response_model=list[TrendingAppOut])
def get_trending_apps(
    chart_type: ChartType | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_trending_apps(
        db, platform=Platform.GOOGLE_PLAY, chart_type=chart_type, category=category, limit=limit
    )
