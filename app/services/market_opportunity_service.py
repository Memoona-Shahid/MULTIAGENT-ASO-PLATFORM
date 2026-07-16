"""Persistence/query helpers for MarketOpportunity rows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import MarketOpportunity


def save_market_opportunities(
    db: Session, opportunities: list[dict], identified_at: datetime
) -> list[MarketOpportunity]:
    rows = []
    for item in opportunities:
        rows.append(MarketOpportunity(
            title=item["title"],
            category=item.get("category"),
            description=item.get("description"),
            supporting_evidence=item.get("supporting_evidence"),
            opportunity_score=item.get("opportunity_score"),
            identified_at=identified_at,
        ))

    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)

    logger.info("Saved {} market opportunities at {}", len(rows), identified_at)
    return rows


def list_market_opportunities(
    db: Session,
    category: str | None = None,
    min_opportunity_score: float | None = None,
    limit: int = 100,
) -> list[MarketOpportunity]:
    stmt = select(MarketOpportunity)
    if category is not None:
        stmt = stmt.where(MarketOpportunity.category == category)
    if min_opportunity_score is not None:
        stmt = stmt.where(MarketOpportunity.opportunity_score >= min_opportunity_score)
    stmt = stmt.order_by(
        MarketOpportunity.opportunity_score.desc().nulls_last(),
        MarketOpportunity.identified_at.desc(),
    ).limit(limit)
    return list(db.scalars(stmt))
