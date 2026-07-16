"""Signal client for Market Opportunity synthesis (Module 7)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import ChartType, Competitor, Keyword, Review, TrendingApp


class MarketSignalClient:
    """Fetches synthesized inputs from local DB tables (no external APIs)."""

    def fetch_trend_signals(self, db: Session, limit: int = 300) -> list[TrendingApp]:
        stmt = (
            select(TrendingApp)
            .where(TrendingApp.chart_type.in_([ChartType.FAST_GROWING, ChartType.TOP_FREE, ChartType.TOP_GROSSING]))
            .order_by(TrendingApp.captured_at.desc(), TrendingApp.rank.asc().nulls_last())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_keyword_signals(self, db: Session, min_opportunity_score: float = 55.0, limit: int = 300) -> list[Keyword]:
        stmt = (
            select(Keyword)
            .where(Keyword.opportunity_score >= min_opportunity_score)
            .order_by(Keyword.opportunity_score.desc().nulls_last(), Keyword.captured_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_competitor_signals(self, db: Session, limit: int = 200) -> list[Competitor]:
        stmt = select(Competitor).order_by(Competitor.last_analyzed_at.desc()).limit(limit)
        return list(db.scalars(stmt))

    def fetch_review_signals(self, db: Session, limit: int = 500) -> list[Review]:
        stmt = (
            select(Review)
            .where(
                (Review.sentiment == "negative")
                | (Review.mentions_bug.is_(True))
                | (Review.mentions_feature_request.is_(True))
            )
            .order_by(Review.captured_at.desc(), Review.posted_at.desc().nulls_last())
            .limit(limit)
        )
        return list(db.scalars(stmt))
