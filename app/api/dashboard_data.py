"""
Dashboard overview API — aggregated intelligence for the browser UI.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.coordinator_agent import CoordinatorAgent
from app.core.database import get_db
from app.models.db_models import (
    Competitor,
    Keyword,
    MarketOpportunity,
    MemoryEntry,
    ProductIdea,
    Report,
    ReportFormat,
    Review,
    TrendingApp,
)
from app.models.schemas import ProductIdeaOut, ReportOut
from app.services.market_opportunity_service import list_market_opportunities
from app.services.report_service import list_reports
from app.utils.category_normalize import normalize_category
from app.utils.idea_narrative import build_detail_sections

router = APIRouter()


def _diverse_opportunities(db: Session, limit: int = 8) -> list:
    rows = list_market_opportunities(db, min_opportunity_score=0, limit=max(limit * 15, 100))
    seen: set[str] = set()
    out = []
    for row in rows:
        cat = normalize_category(row.category) or f"id:{row.id}"
        if cat in seen:
            continue
        seen.add(cat)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _diverse_ideas(db: Session, limit: int = 10) -> list:
    # Prefer newest ideas so the dashboard reflects the latest pipeline run.
    rows = list(
        db.scalars(
            select(ProductIdea)
            .order_by(ProductIdea.generated_at.desc(), ProductIdea.confidence_score.desc().nulls_last())
            .limit(max(limit * 20, 100))
        )
    )
    seen: set[str] = set()
    out = []
    for row in rows:
        key = (row.title or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _diverse_keywords(rows: list, limit: int = 8) -> list:
    seen: set[str] = set()
    out = []
    for row in rows:
        term = (row.term or "").strip().lower()
        root = term.split()[0] if term else ""
        if not root or root in seen:
            continue
        seen.add(root)
        out.append(row)
        if len(out) >= limit:
            break
    return out or rows[:limit]


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db)) -> dict:
    trends = list(
        db.scalars(
            select(TrendingApp)
            .order_by(TrendingApp.captured_at.desc(), TrendingApp.rank.asc().nulls_last())
            .limit(12)
        )
    )
    opportunities = _diverse_opportunities(db, limit=8)
    ideas = _diverse_ideas(db, limit=10)
    reports = list_reports(db, limit=5)
    keywords = list(
        db.scalars(
            select(Keyword)
            .order_by(Keyword.opportunity_score.desc().nulls_last(), Keyword.captured_at.desc())
            .limit(40)
        )
    )
    keywords = _diverse_keywords(keywords, limit=8)

    latest_report = reports[0] if reports else None
    report_preview = None
    if latest_report and latest_report.file_path:
        path = Path(latest_report.file_path)
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            report_preview = text[:4000]

    return {
        "counts": {
            "trends": db.scalar(select(func.count()).select_from(TrendingApp)) or 0,
            "keywords": db.scalar(select(func.count()).select_from(Keyword)) or 0,
            "competitors": db.scalar(select(func.count()).select_from(Competitor)) or 0,
            "reviews": db.scalar(select(func.count()).select_from(Review)) or 0,
            "opportunities": db.scalar(select(func.count()).select_from(MarketOpportunity)) or 0,
            "ideas": db.scalar(select(func.count()).select_from(ProductIdea)) or 0,
            "reports": db.scalar(select(func.count()).select_from(Report)) or 0,
            "memory": db.scalar(select(func.count()).select_from(MemoryEntry)) or 0,
        },
        "trends": [_trend(row) for row in trends],
        "keywords": [_keyword(row) for row in keywords],
        "opportunities": [_opportunity(row) for row in opportunities],
        "ideas": [_idea(row) for row in ideas],
        "reports": [_report(row) for row in reports],
        "latest_report_preview": report_preview,
        "latest_report": _report(latest_report) if latest_report else None,
    }


@router.post("/run-daily")
def run_daily_intelligence(
    report_format: ReportFormat = Query(default=ReportFormat.MARKDOWN),
    opportunity_limit: int = Query(default=10, ge=1, le=50),
    ideas_per_opportunity: int = Query(default=1, ge=1, le=3),
    use_crewai: bool | None = Query(
        default=None,
        description="Override ORCHESTRATION_MODE. True forces CrewAI; False forces direct coordinator.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    agent = CoordinatorAgent()
    return agent.run_daily_pipeline(
        db,
        synthesize_opportunities=True,
        opportunity_limit=opportunity_limit,
        ideas_per_opportunity=ideas_per_opportunity,
        report_format=report_format,
        consolidate_memory=False,
        use_crewai=use_crewai,
    )


@router.get("/ideas/{idea_id}")
def get_idea_detail(idea_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(ProductIdea, idea_id)
    if row is None:
        return {"error": "Idea not found"}

    opportunity = None
    if row.source_opportunity_id:
        opp = db.get(MarketOpportunity, row.source_opportunity_id)
        if opp is not None:
            opportunity = _opportunity(opp)

    return {
        "idea": ProductIdeaOut.model_validate(row).model_dump(mode="json"),
        "opportunity": opportunity,
        "detail_sections": build_detail_sections(
            ProductIdeaOut.model_validate(row).model_dump(mode="json"),
            opportunity,
        ),
    }


@router.get("/reports/{report_id}")
def get_report_detail(report_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(Report, report_id)
    if row is None:
        return {"error": "Report not found"}
    content = None
    if row.file_path:
        path = Path(row.file_path)
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "report": ReportOut.model_validate(row).model_dump(mode="json"),
        "content": content,
    }


def _trend(row: TrendingApp) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "platform": row.platform.value if hasattr(row.platform, "value") else row.platform,
        "category": row.category,
        "chart_type": row.chart_type.value if hasattr(row.chart_type, "value") else row.chart_type,
        "rank": row.rank,
        "rating": row.rating,
        "icon_url": row.icon_url,
    }


def _keyword(row: Keyword) -> dict:
    return {
        "id": row.id,
        "term": row.term,
        "platform": row.platform.value if hasattr(row.platform, "value") else row.platform,
        "opportunity_score": row.opportunity_score,
        "search_volume": row.search_volume,
        "difficulty_score": row.difficulty_score,
    }


def _opportunity(row: MarketOpportunity) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "category": row.category,
        "description": row.description,
        "opportunity_score": row.opportunity_score,
        "identified_at": row.identified_at.isoformat() if row.identified_at else None,
    }


def _idea(row: ProductIdea) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "idea_type": row.idea_type,
        "problem_statement": row.problem_statement,
        "proposed_solution": row.proposed_solution,
        "target_audience": row.target_audience,
        "monetization_strategy": row.monetization_strategy,
        "confidence_score": row.confidence_score,
        "source_opportunity_id": row.source_opportunity_id,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


def _report(row: Report) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "report_type": row.report_type.value if hasattr(row.report_type, "value") else row.report_type,
        "report_format": row.report_format.value if hasattr(row.report_format, "value") else row.report_format,
        "summary": row.summary,
        "file_path": row.file_path,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "period_start": row.period_start.isoformat() if row.period_start else None,
        "period_end": row.period_end.isoformat() if row.period_end else None,
    }
