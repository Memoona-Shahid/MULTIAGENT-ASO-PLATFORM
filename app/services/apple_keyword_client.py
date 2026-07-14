"""
Apple keyword research client — two data sources, both free/keyless:

1. Search Hints ("MZSearchHints") — Apple's own autocomplete endpoint.
   https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?clientApplication=Software&term=<term>
   UNDOCUMENTED/UNOFFICIAL: this isn't a published Apple API, just the same
   endpoint the App Store app itself calls for autocomplete. It's widely
   used by ASO tools (confirmed via Apple developer forums and multiple ASO
   write-ups), but Apple could change or remove it without notice — same
   risk class as the RSS chart feed hitting a 404 in Module 2. Suggestion
   ORDER is the signal: ASO literature consistently treats earlier
   suggestions as more popular searches, which is what search_volume below
   is derived from.

2. iTunes Search API (`itunes.apple.com/search`) — the same official,
   stable domain already used for chart details in Module 2. `resultCount`
   here is used as a competition proxy: how many apps match this term.

IMPORTANT — what search_volume and competition_count actually are:
Apple does not expose real search volume or keyword difficulty without a
paid Apple Search Ads account. Nothing free gives you that. What this
client provides are DEFENSIBLE PROXIES commonly used in the ASO industry
when the real numbers aren't accessible:
  - search_volume: derived from autocomplete position (earlier = more
    popular), not an actual search count.
  - competition_count: number of apps currently matching the term in
    search results, not a true difficulty score.
See app/services/keyword_scoring_service.py for how these get combined.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.utils.retry import with_retry

HINTS_URL = "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
SEARCH_URL = "https://itunes.apple.com/search"

MAX_COMPETITION_RESULTS = 200  # Apple's search API hard cap on `limit`


class KeywordSourceUnavailableError(Exception):
    """Raised when Apple's keyword data sources are unreachable or return an
    unexpected shape (e.g. the unofficial hints endpoint changed/broke)."""


class TransientAPIError(Exception):
    """Raised for retryable failures — network errors, timeouts, 5xx responses."""


class AppleKeywordClient:
    def __init__(self, country: str | None = None, timeout: int | None = None):
        self.country = country or settings.app_store_country
        self.timeout = timeout or settings.request_timeout_seconds

    @with_retry(exceptions=(TransientAPIError, httpx.TransportError))
    def _get(self, url: str, params: dict) -> dict:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            if response.status_code >= 500:
                raise TransientAPIError(f"{response.status_code} from {url}")
            response.raise_for_status()
            return response.json()

    def fetch_suggestions(self, term: str, limit: int = 10) -> list[str]:
        """Autocomplete suggestions for a seed term, in Apple's own popularity order.

        Raises KeywordSourceUnavailableError if the endpoint fails or its
        response doesn't match the expected shape.
        """
        params = {"clientApplication": "Software", "media": "software", "term": term}
        try:
            data = self._get(HINTS_URL, params)
        except (httpx.HTTPStatusError, TransientAPIError) as exc:
            raise KeywordSourceUnavailableError(
                f"Apple search hints unavailable for term '{term}': {exc}"
            ) from exc

        hints = data.get("hints")
        if hints is None:
            raise KeywordSourceUnavailableError(
                f"Apple search hints returned an unexpected response shape for '{term}' "
                "— the unofficial endpoint may have changed."
            )

        suggestions = [h.get("term") for h in hints if h.get("term")]
        return suggestions[:limit]

    def fetch_competition_count(self, term: str) -> int:
        """Number of apps matching this term in App Store search — a
        competition proxy, capped at Apple's max result limit (200)."""
        params = {
            "term": term,
            "country": self.country,
            "entity": "software",
            "limit": MAX_COMPETITION_RESULTS,
        }
        try:
            data = self._get(SEARCH_URL, params)
        except (httpx.HTTPStatusError, TransientAPIError) as exc:
            raise KeywordSourceUnavailableError(
                f"iTunes search unavailable for term '{term}': {exc}"
            ) from exc

        return int(data.get("resultCount", 0))
