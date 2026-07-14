"""
Keyword Research Agent (Requirement 3: high-volume, low-competition keywords).

For each seed term, on each platform:
  1. Fetch autocomplete suggestions (position = popularity proxy).
  2. For each suggestion, fetch a competition count (# apps matching it).
  3. Score volume/difficulty/opportunity (see keyword_scoring_service.py —
     these are heuristic proxies, not real search-volume data; no free
     source for that exists on either store).
  4. Persist as Keyword rows.

Seed terms are supplied by the caller (e.g. category names, competitor app
names, or manually chosen terms an ASO strategist wants to expand on) —
this agent doesn't invent them from nothing.

Failures are scoped per (seed, platform) pair and skipped gracefully,
same pattern as the chart research agents: one bad seed/source doesn't
kill the whole run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.db_models import Platform
from app.services.apple_keyword_client import AppleKeywordClient
from app.services.apple_keyword_client import KeywordSourceUnavailableError as AppleSourceUnavailable
from app.services.google_play_keyword_client import GooglePlayKeywordClient
from app.services.google_play_keyword_client import (
    KeywordSourceUnavailableError as GooglePlaySourceUnavailable,
)
from app.services.keyword_scoring_service import (
    difficulty_score_from_competition,
    opportunity_score,
    volume_score_from_position,
)
from app.services.keyword_service import save_keywords

DEFAULT_SUGGESTIONS_PER_SEED = 10
DEFAULT_PLATFORMS = (Platform.APP_STORE, Platform.GOOGLE_PLAY)


class KeywordResearchAgent:
    def __init__(
        self,
        apple_client: AppleKeywordClient | None = None,
        google_play_client: GooglePlayKeywordClient | None = None,
    ):
        self.apple_client = apple_client or AppleKeywordClient()
        self.google_play_client = google_play_client or GooglePlayKeywordClient()

    def run(
        self,
        db: Session,
        seed_terms: list[str],
        platforms: list[Platform] | None = None,
        suggestions_per_seed: int = DEFAULT_SUGGESTIONS_PER_SEED,
    ) -> dict:
        if not seed_terms:
            raise ValueError("seed_terms must be a non-empty list")

        platforms = platforms or list(DEFAULT_PLATFORMS)
        captured_at = datetime.now(timezone.utc)
        summary: dict = {
            "captured_at": captured_at.isoformat(),
            "seeds": {},
            "skipped": {},
            "total_keywords": 0,
        }

        for seed in seed_terms:
            for platform in platforms:
                key = f"{seed}::{platform.value}"
                try:
                    saved = self._research_seed(db, seed, platform, suggestions_per_seed, captured_at)
                    summary["seeds"][key] = len(saved)
                    summary["total_keywords"] += len(saved)
                except (AppleSourceUnavailable, GooglePlaySourceUnavailable) as exc:
                    logger.warning("Skipping keyword research for {}: {}", key, exc)
                    summary["skipped"][key] = str(exc)

        logger.info("KeywordResearchAgent run complete: {}", summary)
        return summary

    def _research_seed(
        self, db: Session, seed: str, platform: Platform, limit: int, captured_at: datetime
    ) -> list:
        client, max_results = self._client_for(platform)

        suggestions = client.fetch_suggestions(seed, limit=limit)
        if not suggestions:
            return []

        keywords = []
        for position, term in enumerate(suggestions, start=1):
            try:
                competition_count = client.fetch_competition_count(term)
            except (AppleSourceUnavailable, GooglePlaySourceUnavailable) as exc:
                logger.warning(
                    "Competition lookup failed for '{}' ({}), skipping this term: {}",
                    term, platform, exc,
                )
                continue

            volume = volume_score_from_position(position)
            difficulty = difficulty_score_from_competition(competition_count, max_results)
            opportunity = opportunity_score(volume, difficulty)

            keywords.append({
                "term": term,
                "platform": platform,
                "search_volume": volume,
                "difficulty_score": difficulty,
                "opportunity_score": opportunity,
                "related_apps": {"seed": seed, "autocomplete_position": position},
            })

        if not keywords:
            return []

        return save_keywords(db, keywords, captured_at)

    def _client_for(self, platform: Platform):
        if platform == Platform.APP_STORE:
            from app.services.apple_keyword_client import MAX_COMPETITION_RESULTS
            return self.apple_client, MAX_COMPETITION_RESULTS
        if platform == Platform.GOOGLE_PLAY:
            from app.services.google_play_keyword_client import MAX_COMPETITION_RESULTS
            return self.google_play_client, MAX_COMPETITION_RESULTS
        raise ValueError(f"Unsupported platform for keyword research: {platform}")
