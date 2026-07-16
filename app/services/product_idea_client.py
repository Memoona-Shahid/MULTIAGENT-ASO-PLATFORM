"""Source client for the AI Idea Generator Agent (Module 8)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import MarketOpportunity
from app.utils.category_normalize import normalize_category


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
        diversify_by_category: bool = True,
    ) -> list[MarketOpportunity]:
        if opportunity_ids:
            rows = []
            for opp_id in opportunity_ids:
                row = db.get(MarketOpportunity, opp_id)
                if row is not None:
                    rows.append(row)
            return rows

        # Pull a wider pool, then keep the best opportunity per category so
        # idea generation is not stuck on Fitness/Habit duplicates.
        fetch_limit = max(limit * 20, 200) if diversify_by_category else limit
        stmt = select(MarketOpportunity).order_by(
            MarketOpportunity.opportunity_score.desc().nulls_last(),
            MarketOpportunity.identified_at.desc(),
        )
        if min_opportunity_score is not None:
            stmt = stmt.where(MarketOpportunity.opportunity_score >= min_opportunity_score)
        stmt = stmt.limit(fetch_limit)
        rows = list(db.scalars(stmt))

        if not diversify_by_category:
            return rows[:limit]

        seen_categories: set[str] = set()
        diverse: list[MarketOpportunity] = []
        for row in rows:
            category = normalize_category(row.category) or f"id:{row.id}"
            if category in seen_categories:
                continue
            seen_categories.add(category)
            diverse.append(row)
            if len(diverse) >= limit:
                break
        return diverse
