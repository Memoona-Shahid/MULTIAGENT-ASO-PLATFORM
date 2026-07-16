"""Source client for the AI Idea Generator Agent (Module 8)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import MarketOpportunity


class ProductIdeaSourceUnavailableError(Exception):
    """Raised when no usable market opportunities are available for idea generation."""


class ProductIdeaSourceClient:
    """Fetches MarketOpportunity rows from the local DB — no external APIs."""

    def fetch_opportunities(
        self,
        db: Session,
        opportunity_ids: list[int] | None = None,
        min_opportunity_score: float | None = None,
        limit: int = 50,
    ) -> list[MarketOpportunity]:
        if opportunity_ids:
            rows = []
            for opp_id in opportunity_ids:
                row = db.get(MarketOpportunity, opp_id)
                if row is not None:
                    rows.append(row)
            return rows

        stmt = select(MarketOpportunity).order_by(
            MarketOpportunity.opportunity_score.desc().nulls_last(),
            MarketOpportunity.identified_at.desc(),
        )
        if min_opportunity_score is not None:
            stmt = stmt.where(MarketOpportunity.opportunity_score >= min_opportunity_score)
        stmt = stmt.limit(limit)
        return list(db.scalars(stmt))
