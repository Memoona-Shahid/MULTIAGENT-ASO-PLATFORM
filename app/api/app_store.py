"""
API routes for App Store trending data (Module 2).

POST /api/app-store/research  -> runs the agent synchronously, returns a summary
GET  /api/app-store/trending  -> lists the most recent snapshot, with filters
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.app_store_research_agent import AppStoreResearchAgent
from app.core.database import get_db
from app.models.db_models import ChartType, Platform
from app.models.schemas import TrendingAppOut
from app.services.trending_app_service import list_trending_apps

router = APIRouter()


@router.post("/research")
def trigger_research(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Run the App Store Research Agent now. Synchronous — Module 9's scheduler
    will be what calls this automatically on a daily cadence in production."""
    agent = AppStoreResearchAgent()
    return agent.run(db, limit=limit)


@router.get("/trending", response_model=list[TrendingAppOut])
def get_trending_apps(
    chart_type: ChartType | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_trending_apps(
        db, platform=Platform.APP_STORE, chart_type=chart_type, category=category, limit=limit
    )
