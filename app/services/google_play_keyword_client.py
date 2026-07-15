"""
Google Play keyword research client — reuses `gplay-scraper` (already
depended on for Module 3's chart data).

Two methods, same proxy-metric caveat as the Apple client
(app/services/apple_keyword_client.py) applies here too — no real search
volume or difficulty data is available for free from Google either:

  - fetch_suggestions: `suggest_analyze()` — Google Play's own autocomplete,
    in Google's popularity order (used as the search_volume proxy).
  - fetch_competition_count: `len(search_analyze())` — number of apps
    matching the term in Play Store search, capped at the requested count
    (used as the competition proxy).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger

MAX_COMPETITION_RESULTS = 100  # gplay-scraper's practical search count ceiling


class KeywordSourceUnavailableError(Exception):
    """Raised when Google Play's keyword data sources return nothing usable."""


class GooglePlayKeywordClient:
    def __init__(self, country: str | None = None, lang: str = "en"):
        self.country = country or settings.google_play_country
        self.lang = lang
        self._scraper = self._build_scraper()

    def _build_scraper(self):
        try:
            from gplay_scraper import GPlayScraper
        except ModuleNotFoundError as exc:
            raise KeywordSourceUnavailableError(
                "gplay-scraper is not installed; install project requirements to use Google Play keyword research."
            ) from exc
        return GPlayScraper()

    def fetch_suggestions(self, term: str, limit: int = 10) -> list[str]:
        try:
            suggestions = self._scraper.suggest_analyze(
                term, count=limit, lang=self.lang, country=self.country
            )
        except Exception as exc:  # noqa: BLE001 - gplay-scraper's own exception types vary
            raise KeywordSourceUnavailableError(
                f"Google Play suggestions unavailable for term '{term}': {exc}"
            ) from exc

        if not suggestions:
            raise KeywordSourceUnavailableError(
                f"Google Play returned no suggestions for term '{term}' — could be "
                "a genuinely low-interest term or a transient scraping failure."
            )
        return suggestions[:limit]

    def fetch_competition_count(self, term: str) -> int:
        try:
            results = self._scraper.search_analyze(
                term, count=MAX_COMPETITION_RESULTS, lang=self.lang, country=self.country
            )
        except Exception as exc:  # noqa: BLE001
            raise KeywordSourceUnavailableError(
                f"Google Play search unavailable for term '{term}': {exc}"
            ) from exc

        return len(results or [])
