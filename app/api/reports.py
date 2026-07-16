"""
API routes for Report Generator (Module 9).

POST /api/reports/generate  -> generates a daily/weekly report
GET  /api/reports             -> lists saved reports
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.report_generator_agent import ReportGeneratorAgent
from app.core.database import get_db
from app.models.db_models import ReportFormat, ReportType
from app.models.schemas import ReportGenerateRequest, ReportOut
from app.services.report_service import list_reports

router = APIRouter()


@router.post("/generate")
def generate_report(
    request: ReportGenerateRequest,
    db: Session = Depends(get_db),
) -> dict:
    agent = ReportGeneratorAgent()
    return agent.run(
        db,
        report_type=request.report_type,
        report_format=request.report_format,
        generate_ideas=request.generate_ideas,
        min_opportunity_score=request.min_opportunity_score,
        ideas_per_opportunity=request.ideas_per_opportunity,
        opportunity_limit=request.opportunity_limit,
    )


@router.get("", response_model=list[ReportOut])
def get_reports(
    report_type: ReportType | None = Query(default=None),
    report_format: ReportFormat | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return list_reports(
        db,
        report_type=report_type,
        report_format=report_format,
        limit=limit,
    )
