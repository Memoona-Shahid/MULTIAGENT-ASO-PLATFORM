"""Persistence/query helpers for Report rows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Report, ReportFormat, ReportType


def save_report(db: Session, report: dict, generated_at: datetime) -> Report:
    row = Report(
        report_type=report["report_type"],
        report_format=report["report_format"],
        title=report["title"],
        summary=report.get("summary"),
        file_path=report.get("file_path"),
        period_start=report.get("period_start"),
        period_end=report.get("period_end"),
        generated_at=generated_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Saved {} report '{}' at {}", row.report_type.value, row.title, generated_at)
    return row


def list_reports(
    db: Session,
    report_type: ReportType | None = None,
    report_format: ReportFormat | None = None,
    limit: int = 50,
) -> list[Report]:
    stmt = select(Report)
    if report_type is not None:
        stmt = stmt.where(Report.report_type == report_type)
    if report_format is not None:
        stmt = stmt.where(Report.report_format == report_format)
    stmt = stmt.order_by(Report.generated_at.desc()).limit(limit)
    return list(db.scalars(stmt))
