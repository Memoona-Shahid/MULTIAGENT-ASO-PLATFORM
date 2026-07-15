"""
Reviews Intelligence Agent (Requirement 5).

For tracked competitors, this agent:
  1. Pulls a bounded sample of recent store reviews.
  2. Scores sentiment and extracts bug / feature-request signals.
  3. Persists analyzed Review rows for later opportunity synthesis.

Like the earlier agents, it is plain Python orchestration code, not a CrewAI
agent yet. CrewAI wrapping happens in Module 12.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Competitor, Platform
from app.services.competitor_service import list_competitors
from app.services.review_client import AppleReviewClient, GooglePlayReviewClient, ReviewSourceUnavailableError
from app.services.review_service import analyze_review_payload, review_summary, save_analyzed_reviews

DEFAULT_REVIEWS_PER_COMPETITOR = 50
DEFAULT_TRACKED_COMPETITOR_LIMIT = 100
MAX_REVIEWS_PER_COMPETITOR = 200


class ReviewsIntelligenceAgent:
    def __init__(
        self,
        apple_client: AppleReviewClient | None = None,
        google_play_client: GooglePlayReviewClient | None = None,
    ):
        self.apple_client = apple_client or AppleReviewClient()
        self.google_play_client = google_play_client

    def run(
        self,
        db: Session,
        competitor_ids: list[int] | None = None,
        platform: Platform | None = None,
        reviews_per_competitor: int = DEFAULT_REVIEWS_PER_COMPETITOR,
        tracked_competitor_limit: int = DEFAULT_TRACKED_COMPETITOR_LIMIT,
    ) -> dict:
        if reviews_per_competitor < 0 or reviews_per_competitor > MAX_REVIEWS_PER_COMPETITOR:
            raise ValueError(f"reviews_per_competitor must be between 0 and {MAX_REVIEWS_PER_COMPETITOR}")

        captured_at = datetime.now(timezone.utc)
        summary: dict = {
            "captured_at": captured_at.isoformat(),
            "competitors": {},
            "skipped": {},
            "total_competitors": 0,
            "total_reviews": 0,
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "bugs": 0,
            "feature_requests": 0,
        }

        competitors = self._resolve_competitors(db, competitor_ids, platform, tracked_competitor_limit, summary)
        for competitor in competitors:
            key = f"{competitor.platform.value}::{competitor.store_app_id}"
            try:
                raw_reviews = self._client_for(competitor.platform).fetch_reviews(
                    competitor.store_app_id,
                    limit=reviews_per_competitor,
                )
            except ReviewSourceUnavailableError as exc:
                logger.warning("Skipping review intelligence for {}: {}", key, exc)
                summary["skipped"][key] = str(exc)
                continue

            analyzed_reviews = [analyze_review_payload(review) for review in raw_reviews]
            saved = save_analyzed_reviews(db, competitor, analyzed_reviews, captured_at)
            competitor_summary = review_summary(saved)

            summary["competitors"][key] = {
                "competitor_id": competitor.id,
                "reviews": len(saved),
                "sentiment": {
                    "positive": competitor_summary["positive"],
                    "neutral": competitor_summary["neutral"],
                    "negative": competitor_summary["negative"],
                },
                "bugs": competitor_summary["bugs"],
                "feature_requests": competitor_summary["feature_requests"],
            }
            summary["total_competitors"] += 1
            summary["total_reviews"] += len(saved)
            summary["bugs"] += competitor_summary["bugs"]
            summary["feature_requests"] += competitor_summary["feature_requests"]
            for sentiment in ("positive", "neutral", "negative"):
                summary["sentiment"][sentiment] += competitor_summary[sentiment]

        logger.info("ReviewsIntelligenceAgent run complete: {}", summary)
        return summary

    def _client_for(self, platform: Platform):
        if platform == Platform.APP_STORE:
            return self.apple_client
        if platform == Platform.GOOGLE_PLAY:
            if self.google_play_client is None:
                self.google_play_client = GooglePlayReviewClient()
            return self.google_play_client
        raise ValueError(f"Unsupported platform for reviews intelligence: {platform}")

    def _resolve_competitors(
        self,
        db: Session,
        competitor_ids: list[int] | None,
        platform: Platform | None,
        tracked_competitor_limit: int,
        summary: dict,
    ) -> list[Competitor]:
        if competitor_ids:
            competitors = []
            for competitor_id in competitor_ids:
                competitor = db.get(Competitor, competitor_id)
                if competitor is None:
                    summary["skipped"][f"competitor_id::{competitor_id}"] = "Competitor not found"
                    continue
                if platform is not None and competitor.platform != platform:
                    summary["skipped"][f"competitor_id::{competitor_id}"] = (
                        f"Competitor platform is {competitor.platform.value}, not {platform.value}"
                    )
                    continue
                competitors.append(competitor)
            return competitors

        return list_competitors(db, platform=platform, limit=tracked_competitor_limit)
