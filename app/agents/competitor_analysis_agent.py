"""
Competitor Analysis Agent (Requirement 4).

For each requested competitor app:
  1. Fetch normalized store details (downloads/install range where available,
     ratings, screenshots, pricing, feature hints, monetization signals).
  2. Fetch a bounded sample of recent reviews.
  3. Persist/update the Competitor row and append sampled Review rows.

Failures are scoped per app/source. A missing app or broken reviews source is
recorded in the returned `skipped` field and never crashes the whole run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Platform
from app.services.competitor_client import (
    AppleCompetitorClient,
    CompetitorSourceUnavailableError,
    GooglePlayCompetitorClient,
)
from app.services.competitor_service import save_competitor_analysis

DEFAULT_REVIEWS_PER_APP = 20
DEFAULT_MAX_REVIEWS_PER_APP = 100


class CompetitorAnalysisAgent:
    def __init__(
        self,
        apple_client: AppleCompetitorClient | None = None,
        google_play_client: GooglePlayCompetitorClient | None = None,
    ):
        self.apple_client = apple_client or AppleCompetitorClient()
        self.google_play_client = google_play_client

    def run(
        self,
        db: Session,
        targets: list[dict[str, Any]],
        reviews_per_app: int = DEFAULT_REVIEWS_PER_APP,
    ) -> dict:
        if not targets:
            raise ValueError("targets must be a non-empty list")
        if reviews_per_app < 0 or reviews_per_app > DEFAULT_MAX_REVIEWS_PER_APP:
            raise ValueError(f"reviews_per_app must be between 0 and {DEFAULT_MAX_REVIEWS_PER_APP}")

        analyzed_at = datetime.now(timezone.utc)
        summary: dict = {
            "captured_at": analyzed_at.isoformat(),
            "competitors": {},
            "skipped": {},
            "total_competitors": 0,
            "total_reviews": 0,
        }

        for target in targets:
            platform, app_id = self._normalize_target(target)
            key = f"{platform.value}::{app_id}"
            try:
                competitor_data = self._client_for(platform).fetch_details(app_id)
            except CompetitorSourceUnavailableError as exc:
                logger.warning("Skipping competitor {}: {}", key, exc)
                summary["skipped"][key] = str(exc)
                continue

            reviews = []
            if reviews_per_app:
                try:
                    reviews = self._client_for(platform).fetch_reviews(app_id, limit=reviews_per_app)
                except CompetitorSourceUnavailableError as exc:
                    logger.warning("Skipping reviews for {}: {}", key, exc)
                    summary["skipped"][f"{key}::reviews"] = str(exc)

            competitor, review_rows = save_competitor_analysis(
                db,
                competitor_data,
                reviews,
                analyzed_at,
            )
            summary["competitors"][key] = {
                "competitor_id": competitor.id,
                "reviews": len(review_rows),
            }
            summary["total_competitors"] += 1
            summary["total_reviews"] += len(review_rows)

        logger.info("CompetitorAnalysisAgent run complete: {}", summary)
        return summary

    def _client_for(self, platform: Platform):
        if platform == Platform.APP_STORE:
            return self.apple_client
        if platform == Platform.GOOGLE_PLAY:
            if self.google_play_client is None:
                self.google_play_client = GooglePlayCompetitorClient()
            return self.google_play_client
        raise ValueError(f"Unsupported platform for competitor analysis: {platform}")

    def _normalize_target(self, target: dict[str, Any]) -> tuple[Platform, str]:
        platform = target.get("platform")
        app_id = target.get("store_app_id")
        if not app_id:
            raise ValueError("Each target must include store_app_id")
        if not isinstance(platform, Platform):
            platform = Platform(platform)
        return platform, str(app_id)
