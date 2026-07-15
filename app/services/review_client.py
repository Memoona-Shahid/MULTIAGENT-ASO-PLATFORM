"""
Review source clients for the Reviews Intelligence Agent.

These wrap the store-specific review fetchers introduced for competitor
analysis and expose a narrower fetch_reviews(app_id, limit) contract for
Module 6.
"""

from __future__ import annotations

from app.models.db_models import Platform
from app.services.competitor_client import (
    AppleCompetitorClient,
    CompetitorSourceUnavailableError,
    GooglePlayCompetitorClient,
)


class ReviewSourceUnavailableError(Exception):
    """Raised when a store review source cannot return usable review data."""


class AppleReviewClient:
    def __init__(self, competitor_client: AppleCompetitorClient | None = None):
        self.competitor_client = competitor_client or AppleCompetitorClient()

    def fetch_reviews(self, app_id: str, limit: int = 50) -> list[dict]:
        try:
            reviews = self.competitor_client.fetch_reviews(app_id, limit=limit)
        except CompetitorSourceUnavailableError as exc:
            raise ReviewSourceUnavailableError(str(exc)) from exc

        for review in reviews:
            review["platform"] = Platform.APP_STORE
        return reviews


class GooglePlayReviewClient:
    def __init__(self, competitor_client: GooglePlayCompetitorClient | None = None):
        self.competitor_client = competitor_client

    def fetch_reviews(self, app_id: str, limit: int = 50) -> list[dict]:
        if self.competitor_client is None:
            self.competitor_client = GooglePlayCompetitorClient()

        try:
            reviews = self.competitor_client.fetch_reviews(app_id, limit=limit)
        except CompetitorSourceUnavailableError as exc:
            raise ReviewSourceUnavailableError(str(exc)) from exc

        for review in reviews:
            review["platform"] = Platform.GOOGLE_PLAY
        return reviews
