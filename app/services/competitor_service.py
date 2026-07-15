"""Persistence layer for competitor analyses and sampled reviews."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Competitor, Platform, Review


def save_competitor_analysis(
    db: Session,
    competitor_data: dict,
    reviews: list[dict],
    analyzed_at: datetime,
) -> tuple[Competitor, list[Review]]:
    """Upsert one competitor row and append its latest sampled reviews."""
    competitor = db.scalar(
        select(Competitor).where(
            Competitor.platform == competitor_data["platform"],
            Competitor.store_app_id == str(competitor_data["store_app_id"]),
        )
    )

    if competitor is None:
        competitor = Competitor(
            platform=competitor_data["platform"],
            store_app_id=str(competitor_data["store_app_id"]),
            name=competitor_data["name"],
        )
        db.add(competitor)

    competitor.name = competitor_data["name"]
    competitor.developer = competitor_data.get("developer")
    competitor.category = competitor_data.get("category")
    competitor.estimated_downloads = competitor_data.get("estimated_downloads")
    competitor.rating = competitor_data.get("rating")
    competitor.rating_count = competitor_data.get("rating_count")
    competitor.pricing_model = competitor_data.get("pricing_model")
    competitor.monetization_details = competitor_data.get("monetization_details")
    competitor.screenshots = competitor_data.get("screenshots")
    competitor.features = competitor_data.get("features")
    competitor.last_analyzed_at = analyzed_at

    db.flush()

    review_rows = []
    for review in reviews:
        review_rows.append(Review(
            competitor_id=competitor.id,
            platform=review.get("platform", competitor.platform),
            author=review.get("author"),
            rating=review.get("rating"),
            review_text=review.get("review_text"),
            sentiment=review.get("sentiment"),
            sentiment_score=review.get("sentiment_score"),
            mentions_bug=review.get("mentions_bug", False),
            mentions_feature_request=review.get("mentions_feature_request", False),
            extracted_topics=review.get("extracted_topics"),
            posted_at=review.get("posted_at"),
            captured_at=analyzed_at,
        ))

    db.add_all(review_rows)
    db.commit()
    db.refresh(competitor)
    for row in review_rows:
        db.refresh(row)

    logger.info(
        "Saved competitor analysis for {}:{} with {} reviews",
        competitor.platform,
        competitor.store_app_id,
        len(review_rows),
    )
    return competitor, review_rows


def list_competitors(
    db: Session,
    platform: Platform | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[Competitor]:
    stmt = select(Competitor)
    if platform is not None:
        stmt = stmt.where(Competitor.platform == platform)
    if category is not None:
        stmt = stmt.where(Competitor.category == category)
    stmt = stmt.order_by(Competitor.last_analyzed_at.desc(), Competitor.rating.desc().nulls_last()).limit(limit)

    return list(db.scalars(stmt))


def get_competitor(db: Session, competitor_id: int) -> Competitor | None:
    return db.get(Competitor, competitor_id)


def list_competitor_reviews(db: Session, competitor_id: int, limit: int = 100) -> list[Review]:
    stmt = (
        select(Review)
        .where(Review.competitor_id == competitor_id)
        .order_by(Review.captured_at.desc(), Review.posted_at.desc().nulls_last())
        .limit(limit)
    )
    return list(db.scalars(stmt))
