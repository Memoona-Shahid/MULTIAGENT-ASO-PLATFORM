"""Data client for the Report Generator Agent (Module 9)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import (
    Competitor,
    Keyword,
    MarketOpportunity,
    ProductIdea,
    Review,
    TrendingApp,
)


class ReportDataClient:
    """Fetches platform data from the local DB for report generation."""

    def fetch_trends(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 200,
    ) -> list[TrendingApp]:
        stmt = (
            select(TrendingApp)
            .where(TrendingApp.captured_at >= period_start, TrendingApp.captured_at <= period_end)
            .order_by(TrendingApp.captured_at.desc(), TrendingApp.rank.asc().nulls_last())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_keywords(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 200,
    ) -> list[Keyword]:
        stmt = (
            select(Keyword)
            .where(Keyword.captured_at >= period_start, Keyword.captured_at <= period_end)
            .order_by(Keyword.opportunity_score.desc().nulls_last(), Keyword.captured_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_competitors(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 100,
    ) -> list[Competitor]:
        stmt = (
            select(Competitor)
            .where(Competitor.last_analyzed_at >= period_start, Competitor.last_analyzed_at <= period_end)
            .order_by(Competitor.last_analyzed_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_reviews(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 300,
    ) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.captured_at >= period_start, Review.captured_at <= period_end)
            .order_by(Review.captured_at.desc(), Review.posted_at.desc().nulls_last())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_opportunities(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 100,
    ) -> list[MarketOpportunity]:
        stmt = (
            select(MarketOpportunity)
            .where(
                MarketOpportunity.identified_at >= period_start,
                MarketOpportunity.identified_at <= period_end,
            )
            .order_by(
                MarketOpportunity.opportunity_score.desc().nulls_last(),
                MarketOpportunity.identified_at.desc(),
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_product_ideas(
        self,
        db: Session,
        period_start: datetime,
        period_end: datetime,
        limit: int = 100,
    ) -> list[ProductIdea]:
        stmt = (
            select(ProductIdea)
            .where(ProductIdea.generated_at >= period_start, ProductIdea.generated_at <= period_end)
            .order_by(
                ProductIdea.confidence_score.desc().nulls_last(),
                ProductIdea.generated_at.desc(),
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_latest_product_ideas(self, db: Session, limit: int = 20) -> list[ProductIdea]:
        stmt = (
            select(ProductIdea)
            .order_by(
                ProductIdea.confidence_score.desc().nulls_last(),
                ProductIdea.generated_at.desc(),
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def count_opportunities(self, db: Session) -> int:
        from sqlalchemy import func

        return db.scalar(select(func.count()).select_from(MarketOpportunity)) or 0
