"""Persistence/query helpers for ProductIdea rows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import ProductIdea


def save_product_ideas(db: Session, ideas: list[dict], generated_at: datetime) -> list[ProductIdea]:
    rows = []
    for idea in ideas:
        rows.append(ProductIdea(
            title=idea["title"],
            idea_type=idea.get("idea_type"),
            problem_statement=idea.get("problem_statement"),
            proposed_solution=idea.get("proposed_solution"),
            target_audience=idea.get("target_audience"),
            monetization_strategy=idea.get("monetization_strategy"),
            confidence_score=idea.get("confidence_score"),
            source_opportunity_id=idea.get("source_opportunity_id"),
            generated_at=generated_at,
        ))

    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)

    logger.info("Saved {} product ideas at {}", len(rows), generated_at)
    return rows


def list_product_ideas(
    db: Session,
    idea_type: str | None = None,
    min_confidence_score: float | None = None,
    limit: int = 100,
) -> list[ProductIdea]:
    stmt = select(ProductIdea)
    if idea_type is not None:
        stmt = stmt.where(ProductIdea.idea_type == idea_type)
    if min_confidence_score is not None:
        stmt = stmt.where(ProductIdea.confidence_score >= min_confidence_score)
    stmt = stmt.order_by(
        ProductIdea.confidence_score.desc().nulls_last(),
        ProductIdea.generated_at.desc(),
    ).limit(limit)
    return list(db.scalars(stmt))
