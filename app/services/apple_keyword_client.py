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

   Response is an XML plist (not JSON). Without the X-Apple-Store-Front
   header the hints array comes back empty.

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

import json
import plistlib

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.utils.retry import with_retry

HINTS_URL = "https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints"
SEARCH_URL = "https://itunes.apple.com/search"

MAX_COMPETITION_RESULTS = 200  # Apple's search API hard cap on `limit`

# Apple storefront IDs used by X-Apple-Store-Front (id-language,platform).
# Platform "29" is the conventional value used by App Store clients/ASO tools.
_STORE_FRONTS: dict[str, str] = {
    "us": "143441-1,29",
    "gb": "143444-1,29",
    "ca": "143455-1,29",
    "au": "143460-1,29",
    "de": "143443-1,29",
    "fr": "143442-1,29",
    "jp": "143462-1,29",
    "in": "143467-1,29",
    "br": "143503-1,29",
    "mx": "143468-1,29",
}


class KeywordSourceUnavailableError(Exception):
    """Raised when Apple's keyword data sources are unreachable or return an
    unexpected shape (e.g. the unofficial hints endpoint changed/broke)."""


class TransientAPIError(Exception):
    """Raised for retryable failures — network errors, timeouts, 5xx responses."""


class AppleKeywordClient:
    def __init__(self, country: str | None = None, timeout: int | None = None):
        self.country = (country or settings.app_store_country).lower()
        self.timeout = timeout or settings.request_timeout_seconds

    def _store_front(self) -> str:
        front = _STORE_FRONTS.get(self.country)
        if front is None:
            logger.warning(
                "No Apple storefront mapping for country '{}'; falling back to US",
                self.country,
            )
            return _STORE_FRONTS["us"]
        return front

    @with_retry(exceptions=(TransientAPIError, httpx.TransportError))
    def _request(self, url: str, params: dict, headers: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, params=params, headers=headers or {})
            if response.status_code >= 500:
                raise TransientAPIError(f"{response.status_code} from {url}")
            response.raise_for_status()
            return response

    def _get_json(self, url: str, params: dict) -> dict:
        response = self._request(url, params)
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise KeywordSourceUnavailableError(
                f"Expected JSON from {url}, got content-type "
                f"{response.headers.get('content-type')!r}"
            ) from exc

    def _get_plist(self, url: str, params: dict, headers: dict | None = None) -> dict:
        response = self._request(url, params, headers=headers)
        try:
            data = plistlib.loads(response.content)
        except Exception as exc:  # noqa: BLE001 - plistlib raises several subtypes
            raise KeywordSourceUnavailableError(
                f"Expected plist from {url}, got content-type "
                f"{response.headers.get('content-type')!r}"
            ) from exc
        if not isinstance(data, dict):
            raise KeywordSourceUnavailableError(
                f"Apple search hints returned a non-dict plist root from {url}"
            )
        return data

    def fetch_suggestions(self, term: str, limit: int = 10) -> list[str]:
        """Autocomplete suggestions for a seed term, in Apple's own popularity order.

        Raises KeywordSourceUnavailableError if the endpoint fails or its
        response doesn't match the expected shape.
        """
        params = {"clientApplication": "Software", "media": "software", "term": term}
        headers = {"X-Apple-Store-Front": self._store_front()}
        try:
            data = self._get_plist(HINTS_URL, params, headers=headers)
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

        suggestions = [h.get("term") for h in hints if isinstance(h, dict) and h.get("term")]
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
            data = self._get_json(SEARCH_URL, params)
        except (httpx.HTTPStatusError, TransientAPIError) as exc:
            raise KeywordSourceUnavailableError(
                f"iTunes search unavailable for term '{term}': {exc}"
            ) from exc

        return int(data.get("resultCount", 0))
