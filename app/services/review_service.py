"""Persistence and lightweight NLP helpers for Review intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Competitor, Platform, Review

POSITIVE_TERMS = {
    "amazing",
    "best",
    "easy",
    "excellent",
    "fast",
    "great",
    "helpful",
    "love",
    "perfect",
    "useful",
}
NEGATIVE_TERMS = {
    "bad",
    "broken",
    "bug",
    "crash",
    "crashes",
    "crashing",
    "error",
    "freeze",
    "freezes",
    "hate",
    "issue",
    "lag",
    "slow",
    "terrible",
    "worst",
}
BUG_TERMS = {
    "bug",
    "broken",
    "cannot",
    "can't",
    "crash",
    "crashes",
    "crashing",
    "error",
    "fails",
    "freeze",
    "freezes",
    "glitch",
    "issue",
    "lag",
    "stuck",
    "won't",
}
FEATURE_REQUEST_PHRASES = {
    "add",
    "feature request",
    "i wish",
    "missing",
    "needs",
    "please add",
    "should have",
    "would be nice",
    "would love",
}
TOPIC_KEYWORDS = {
    "ads": {"ad", "ads", "advertising"},
    "login": {"login", "password", "sign in", "signin"},
    "notifications": {"alert", "notification", "notifications"},
    "onboarding": {"tutorial", "onboarding", "setup"},
    "performance": {"fast", "lag", "slow", "speed", "freeze", "crash"},
    "pricing": {"billing", "pay", "price", "pricing", "subscription"},
    "sync": {"backup", "cloud", "sync"},
    "ui": {"design", "interface", "layout", "ui", "ux"},
}


def analyze_review_payload(review: dict) -> dict:
    """Enrich a raw store review with sentiment, bug/request flags, and topics."""
    text = review.get("review_text") or ""
    rating = _safe_int(review.get("rating"))
    score = sentiment_score(text, rating)
    topics = extract_topics(text)
    mentions_bug = contains_any(text, BUG_TERMS)
    mentions_feature_request = contains_any(text, FEATURE_REQUEST_PHRASES)

    return {
        **review,
        "rating": rating,
        "sentiment_score": score,
        "sentiment": sentiment_label(score),
        "mentions_bug": mentions_bug,
        "mentions_feature_request": mentions_feature_request,
        "extracted_topics": {
            **(review.get("extracted_topics") or {}),
            "topics": topics,
            "signals": {
                "bug_terms": sorted(matched_terms(text, BUG_TERMS)),
                "feature_request_terms": sorted(matched_terms(text, FEATURE_REQUEST_PHRASES)),
            },
        },
    }


def sentiment_score(text: str | None, rating: int | None = None) -> float:
    """Return a simple -1..1 sentiment score from rating + review language."""
    scores = []
    if rating is not None:
        scores.append(max(-1.0, min(1.0, (rating - 3) / 2)))

    text_score = _lexicon_sentiment(text or "")
    if text_score is not None:
        scores.append(text_score)

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def sentiment_label(score: float) -> str:
    if score >= 0.25:
        return "positive"
    if score <= -0.25:
        return "negative"
    return "neutral"


def contains_any(text: str | None, terms: set[str]) -> bool:
    return bool(matched_terms(text, terms))


def matched_terms(text: str | None, terms: set[str]) -> set[str]:
    normalized = f" {(text or '').lower()} "
    return {term for term in terms if f" {term} " in normalized or term in normalized}


def extract_topics(text: str | None) -> list[str]:
    normalized = f" {(text or '').lower()} "
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(f" {keyword} " in normalized or keyword in normalized for keyword in keywords):
            topics.append(topic)
    return topics


def save_analyzed_reviews(
    db: Session,
    competitor: Competitor,
    reviews: list[dict],
    captured_at: datetime,
) -> list[Review]:
    """Insert or update analyzed reviews, deduping by author/text/posted_at."""
    rows = []
    for review in reviews:
        row = _find_existing_review(db, competitor.id, review)
        if row is None:
            row = Review(competitor_id=competitor.id)
            db.add(row)

        row.platform = review.get("platform", competitor.platform)
        row.author = review.get("author")
        row.rating = review.get("rating")
        row.review_text = review.get("review_text")
        row.sentiment = review.get("sentiment")
        row.sentiment_score = review.get("sentiment_score")
        row.mentions_bug = review.get("mentions_bug", False)
        row.mentions_feature_request = review.get("mentions_feature_request", False)
        row.extracted_topics = review.get("extracted_topics")
        row.posted_at = review.get("posted_at")
        row.captured_at = captured_at
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)

    logger.info("Saved {} analyzed reviews for competitor {}", len(rows), competitor.id)
    return rows


def list_reviews(
    db: Session,
    competitor_id: int | None = None,
    platform: Platform | None = None,
    sentiment: str | None = None,
    mentions_bug: bool | None = None,
    mentions_feature_request: bool | None = None,
    limit: int = 100,
) -> list[Review]:
    stmt = select(Review)
    if competitor_id is not None:
        stmt = stmt.where(Review.competitor_id == competitor_id)
    if platform is not None:
        stmt = stmt.where(Review.platform == platform)
    if sentiment is not None:
        stmt = stmt.where(Review.sentiment == sentiment)
    if mentions_bug is not None:
        stmt = stmt.where(Review.mentions_bug == mentions_bug)
    if mentions_feature_request is not None:
        stmt = stmt.where(Review.mentions_feature_request == mentions_feature_request)

    stmt = stmt.order_by(Review.captured_at.desc(), Review.posted_at.desc().nulls_last()).limit(limit)
    return list(db.scalars(stmt))


def review_summary(reviews: list[Review]) -> dict:
    summary = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "bugs": 0,
        "feature_requests": 0,
    }
    for review in reviews:
        if review.sentiment in {"positive", "neutral", "negative"}:
            summary[review.sentiment] += 1
        if review.mentions_bug:
            summary["bugs"] += 1
        if review.mentions_feature_request:
            summary["feature_requests"] += 1
    return summary


def _find_existing_review(db: Session, competitor_id: int, review: dict) -> Review | None:
    return db.scalar(
        select(Review).where(
            Review.competitor_id == competitor_id,
            Review.author == review.get("author"),
            Review.review_text == review.get("review_text"),
            Review.posted_at == review.get("posted_at"),
        )
    )


def _lexicon_sentiment(text: str) -> float | None:
    normalized = text.lower()
    positive = sum(1 for term in POSITIVE_TERMS if term in normalized)
    negative = sum(1 for term in NEGATIVE_TERMS if term in normalized)
    total = positive + negative
    if total == 0:
        return None
    return max(-1.0, min(1.0, (positive - negative) / total))


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
