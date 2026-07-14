"""Persistence layer for Keyword rows — mirrors trending_app_service.py's shape."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Keyword, Platform


def save_keywords(db: Session, keywords: list[dict], captured_at: datetime) -> list[Keyword]:
    """Bulk-insert keyword rows. Each dict needs at minimum: term, platform."""
    rows = []
    for kw in keywords:
        rows.append(Keyword(
            term=kw["term"],
            platform=kw["platform"],
            search_volume=kw.get("search_volume"),
            difficulty_score=kw.get("difficulty_score"),
            opportunity_score=kw.get("opportunity_score"),
            related_apps=kw.get("related_apps"),
            captured_at=captured_at,
        ))
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)

    logger.info("Saved {} keyword rows at {}", len(rows), captured_at)
    return rows


def list_keywords(
    db: Session,
    platform: Platform | None = None,
    min_opportunity_score: float | None = None,
    limit: int = 100,
) -> list[Keyword]:
    stmt = select(Keyword)
    if platform is not None:
        stmt = stmt.where(Keyword.platform == platform)
    if min_opportunity_score is not None:
        stmt = stmt.where(Keyword.opportunity_score >= min_opportunity_score)
    stmt = stmt.order_by(Keyword.opportunity_score.desc().nulls_last(), Keyword.captured_at.desc()).limit(limit)

    return list(db.scalars(stmt))
