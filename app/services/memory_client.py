"""Source client for the Memory Agent (Module 10)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import (
    Competitor,
    Keyword,
    MarketOpportunity,
    MemoryEntry,
    ProductIdea,
    Report,
    Review,
    TrendingApp,
)


class MemorySourceClient:
    """Reads recent platform data and existing memory rows from the local DB."""

    def fetch_recent_trends(self, db: Session, since: datetime, limit: int = 200) -> list[TrendingApp]:
        stmt = (
            select(TrendingApp)
            .where(TrendingApp.captured_at >= since)
            .order_by(TrendingApp.captured_at.desc(), TrendingApp.rank.asc().nulls_last())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_keywords(self, db: Session, since: datetime, limit: int = 200) -> list[Keyword]:
        stmt = (
            select(Keyword)
            .where(Keyword.captured_at >= since)
            .order_by(Keyword.opportunity_score.desc().nulls_last(), Keyword.captured_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_competitors(self, db: Session, since: datetime, limit: int = 100) -> list[Competitor]:
        stmt = (
            select(Competitor)
            .where(Competitor.last_analyzed_at >= since)
            .order_by(Competitor.last_analyzed_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_reviews(self, db: Session, since: datetime, limit: int = 300) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.captured_at >= since)
            .order_by(Review.captured_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_opportunities(
        self, db: Session, since: datetime, limit: int = 100
    ) -> list[MarketOpportunity]:
        stmt = (
            select(MarketOpportunity)
            .where(MarketOpportunity.identified_at >= since)
            .order_by(
                MarketOpportunity.opportunity_score.desc().nulls_last(),
                MarketOpportunity.identified_at.desc(),
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_product_ideas(self, db: Session, since: datetime, limit: int = 100) -> list[ProductIdea]:
        stmt = (
            select(ProductIdea)
            .where(ProductIdea.generated_at >= since)
            .order_by(
                ProductIdea.confidence_score.desc().nulls_last(),
                ProductIdea.generated_at.desc(),
            )
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_recent_reports(self, db: Session, since: datetime, limit: int = 50) -> list[Report]:
        stmt = (
            select(Report)
            .where(Report.generated_at >= since)
            .order_by(Report.generated_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def fetch_memory_entries(
        self,
        db: Session,
        entry_types: list[str] | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        stmt = select(MemoryEntry)
        if entry_types:
            stmt = stmt.where(MemoryEntry.entry_type.in_(entry_types))
        if since is not None:
            stmt = stmt.where(MemoryEntry.created_at >= since)
        stmt = stmt.order_by(MemoryEntry.importance.desc(), MemoryEntry.created_at.desc()).limit(limit)
        return list(db.scalars(stmt))
