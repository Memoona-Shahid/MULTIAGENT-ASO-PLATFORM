"""
Thin client for Google Play Store data via the `gplay-scraper` package.

Google has no official free JSON API for chart rankings or app details the
way Apple does (rss.marketingtools.apple.com / iTunes Lookup). The
well-known `google-play-scraper` package many tutorials reference doesn't
support chart listings at all -- only single-app lookup, search, and
reviews. `gplay-scraper` is a maintained alternative that does support Top
Free / Top Paid / Top Grossing by scraping Google Play's own web pages.

Unlike Apple (which discontinued Top Grossing from its free feed), Google
Play still serves all three chart collections.

IMPORTANT CAVEATS (being a scraper, not an official API):
  1. `gplay-scraper`'s methods internally catch their own errors and return
     an empty list/dict instead of raising. That means a genuinely empty
     chart and a scraping failure (Google changed their page structure,
     rate limiting, etc) look identical from here -- we can't distinguish
     them. Empty results are treated as "unavailable" (ChartUnavailableError),
     same UX as Apple's discontinued-chart case, but the underlying cause
     may differ.
  2. There's no batch detail-lookup like Apple's iTunes Lookup API -- each
     app's rating COUNT requires its own scrape request. For a 100-app
     chart that's 100 sequential requests, which is slow and more likely to
     get rate-limited. Detail enrichment is therefore opt-in
     (fetch_details=False by default) -- the chart listing itself already
     includes a `rating` (score) value, just not the rating count.
"""

from __future__ import annotations

from gplay_scraper import GPlayScraper

from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import ChartType

# Google Play still offers all three chart collections (unlike Apple, which
# discontinued Top Grossing from its free feed).
_CHART_COLLECTIONS: dict[ChartType, str] = {
    ChartType.TOP_FREE: "TOP_FREE",
    ChartType.TOP_PAID: "TOP_PAID",
    ChartType.TOP_GROSSING: "TOP_GROSSING",
}

DEFAULT_CATEGORY = "APPLICATION"  # overall chart across all categories, not games-only


class ChartUnavailableError(Exception):
    """Raised when Google Play has no data for a requested chart."""


class GooglePlayClient:
    """Wraps GPlayScraper with the same fetch_chart/fetch_app_details shape as AppleAppStoreClient."""

    def __init__(self, country: str | None = None, lang: str = "en"):
        self.country = country or settings.google_play_country
        self.lang = lang
        self._scraper = GPlayScraper()

    def fetch_chart(self, chart_type: ChartType, limit: int = 100) -> list[dict]:
        """Fetch a ranked chart. Returns basic app info + rating per rank.

        Raises ChartUnavailableError if this chart type isn't mapped, or if
        Google Play returned no results (see module docstring caveat #1).
        """
        collection = _CHART_COLLECTIONS.get(chart_type)
        if collection is None:
            raise ChartUnavailableError(
                f"{chart_type} is not available from Google Play "
                "(fast-growing is computed, not fetched)."
            )

        logger.debug(
            "Fetching Google Play chart {} ({}) collection={}", chart_type, self.country, collection
        )
        results = self._scraper.list_analyze(
            collection=collection,
            category=DEFAULT_CATEGORY,
            count=limit,
            lang=self.lang,
            country=self.country,
        )

        if not results:
            raise ChartUnavailableError(
                f"Google Play returned no results for chart {chart_type} ({collection}) — "
                "could be a genuinely empty chart or a transient scraping failure "
                "(gplay-scraper swallows the distinction, see module docstring)."
            )

        entries = []
        for rank, item in enumerate(results, start=1):
            entries.append({
                "store_app_id": item.get("appId"),
                "name": item.get("title"),
                "developer": item.get("developer"),
                "category": item.get("genre"),
                "icon_url": item.get("icon"),
                "store_url": item.get("url"),
                "rank": rank,
                "rating": item.get("score"),
                "price": item.get("price"),
            })
        logger.info("Fetched {} entries for chart {} ({})", len(entries), chart_type, self.country)
        return entries

    def fetch_app_details(self, app_ids: list[str]) -> dict[str, dict]:
        """Fetch per-app detail (mainly rating count) one request per app.

        Slower than Apple's batch lookup by design of the underlying site —
        call sparingly, or only for a subset of a large chart, if runtime
        matters (e.g. daily scheduled runs against 100+ apps per chart).
        """
        details: dict[str, dict] = {}
        unique_ids = [i for i in dict.fromkeys(app_ids) if i]

        for app_id in unique_ids:
            try:
                data = self._scraper.app_analyze(app_id, lang=self.lang, country=self.country)
            except Exception as exc:  # noqa: BLE001 - gplay-scraper's own exception types vary
                logger.warning("Failed to fetch Google Play details for {}: {}", app_id, exc)
                continue

            if not data:
                continue

            details[app_id] = {
                "name": data.get("title"),
                "developer": data.get("developer"),
                "category": data.get("genre"),
                "rating": data.get("score"),
                "rating_count": data.get("ratings"),
                "price": data.get("price"),
                "icon_url": data.get("icon"),
                "store_url": data.get("appUrl"),
            }

        logger.info("Fetched details for {}/{} app ids", len(details), len(unique_ids))
        return details
