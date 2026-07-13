"""
Thin client for Apple's two public, keyless JSON endpoints:

1. RSS Marketing Tools feed — chart rankings (Top Free / Top Paid / Top Grossing)
   https://rss.applemarketingtools.com/api/v2/{country}/apps/{chart}/{limit}/apps.json
   Gives id/name/artist/artwork/url but NOT rating, price, or rating count.

2. iTunes Lookup API — full app details, batched by id
   https://itunes.apple.com/lookup?id=1,2,3&country=us
   Gives rating, ratingCount, price, category, etc. Max ~200 ids per call;
   we chunk conservatively at 100 to stay well under Apple's practical limits.

Neither endpoint requires an API key. Both are wrapped with the shared
retry decorator since they're plain HTTP calls that can transiently fail.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import ChartType
from app.utils.retry import with_retry

RSS_BASE_URL = "https://rss.marketingtools.apple.com/api/v2"
LOOKUP_BASE_URL = "https://itunes.apple.com/lookup"

# As of mid-2026, Apple's public RSS Marketing Tools feed only reliably
# serves "top-free" and "top-paid" — the "top-grossing" chart was
# discontinued from this free endpoint and now returns a permanent 404.
# Apple never had a public "fast growing" chart either — we compute that
# ourselves by comparing snapshots. Charts not in this map are treated as
# unavailable and skipped gracefully rather than erroring out the whole run.
_CHART_SLUGS: dict[ChartType, str] = {
    ChartType.TOP_FREE: "top-free",
    ChartType.TOP_PAID: "top-paid",
}

LOOKUP_CHUNK_SIZE = 100


class ChartUnavailableError(Exception):
    """Raised when Apple has no data for a requested chart (permanent, e.g. 404)."""


class TransientAPIError(Exception):
    """Raised for retryable failures — network errors, timeouts, 5xx responses."""


class AppleAppStoreClient:
    """Stateless HTTP client for Apple App Store chart + detail data."""

    def __init__(self, country: str | None = None, timeout: int | None = None):
        self.country = country or settings.app_store_country
        self.timeout = timeout or settings.request_timeout_seconds

    @with_retry(exceptions=(TransientAPIError, httpx.TransportError))
    def _get(self, url: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)

            # Only retry on transient failures. A 4xx is permanent (bad
            # request, discontinued endpoint, etc) and retrying it just
            # burns time on the same guaranteed failure.
            if response.status_code >= 500:
                raise TransientAPIError(f"{response.status_code} from {url}")

            response.raise_for_status()  # raises httpx.HTTPStatusError for 4xx, not retried
            return response.json()

    def fetch_chart(self, chart_type: ChartType, limit: int = 100) -> list[dict]:
        """Fetch a ranked chart from the RSS feed. Returns basic app info per rank.

        Raises ChartUnavailableError if this chart type has no known Apple
        slug, or if Apple returns 404 for it (discontinued/renamed feed).
        """
        slug = _CHART_SLUGS.get(chart_type)
        if slug is None:
            raise ChartUnavailableError(
                f"{chart_type} is not available from Apple's public RSS feed."
            )

        url = f"{RSS_BASE_URL}/{self.country}/apps/{slug}/{limit}/apps.json"
        logger.debug("Fetching Apple chart {} ({}) from {}", chart_type, self.country, url)

        try:
            data = self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ChartUnavailableError(
                    f"Apple returned 404 for chart {chart_type} ({slug}) — "
                    "this chart may have been discontinued or renamed."
                ) from exc
            raise

        results = data.get("feed", {}).get("results", [])

        entries = []
        for rank, item in enumerate(results, start=1):
            genres = item.get("genres") or []
            entries.append({
                "store_app_id": item.get("id"),
                "name": item.get("name"),
                "developer": item.get("artistName"),
                "category": genres[0]["name"] if genres else None,
                "icon_url": item.get("artworkUrl100"),
                "store_url": item.get("url"),
                "rank": rank,
            })
        logger.info("Fetched {} entries for chart {} ({})", len(entries), chart_type, self.country)
        return entries

    def fetch_app_details(self, app_ids: list[str]) -> dict[str, dict]:
        """Batch-fetch rating/price/category details for a list of app store ids.

        Returns a dict keyed by store_app_id (string) -> details dict.
        Missing ids (e.g. delisted apps) are simply absent from the result.
        """
        details: dict[str, dict] = {}
        unique_ids = [i for i in dict.fromkeys(app_ids) if i]  # de-dupe, preserve order

        for start in range(0, len(unique_ids), LOOKUP_CHUNK_SIZE):
            chunk = unique_ids[start:start + LOOKUP_CHUNK_SIZE]
            params = {"id": ",".join(chunk), "country": self.country}
            data = self._get(LOOKUP_BASE_URL, params=params)

            for result in data.get("results", []):
                track_id = str(result.get("trackId"))
                details[track_id] = {
                    "name": result.get("trackName"),
                    "developer": result.get("artistName"),
                    "category": result.get("primaryGenreName"),
                    "rating": result.get("averageUserRating"),
                    "rating_count": result.get("userRatingCount"),
                    "price": result.get("price"),
                    "icon_url": result.get("artworkUrl100"),
                    "store_url": result.get("trackViewUrl"),
                }

        logger.info("Fetched details for {}/{} app ids", len(details), len(unique_ids))
        return details
