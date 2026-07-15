"""
Clients for competitor deep-dives across the App Store and Google Play.

Both clients normalize store-specific responses into the same dict shape the
CompetitorAnalysisAgent persists:
  - app identity, ratings, pricing, screenshots, feature hints, monetization
  - a small sample of recent reviews for the Review table

No API keys are required. Apple uses iTunes Lookup plus the public customer
reviews RSS feed. Google Play reuses the already-selected gplay-scraper
package from Modules 3 and 4.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import Platform
from app.utils.retry import with_retry

APPLE_LOOKUP_URL = "https://itunes.apple.com/lookup"
APPLE_REVIEWS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

DEFAULT_REVIEW_LIMIT = 20
FEATURE_LIMIT = 12


class CompetitorSourceUnavailableError(Exception):
    """Raised when a store source cannot return usable competitor data."""


class TransientAPIError(Exception):
    """Raised for retryable failures such as network errors, timeouts, or 5xx responses."""


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_strings(values: list[Any], limit: int | None = None) -> list[str]:
    cleaned = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if text and text not in cleaned:
            cleaned.append(text)
        if limit is not None and len(cleaned) >= limit:
            break
    return cleaned


def _extract_features(description: str | None, raw_features: Any = None) -> list[str]:
    """Pull lightweight feature hints from store metadata without using an LLM."""
    features = _clean_strings(_as_list(raw_features), limit=FEATURE_LIMIT)
    description = description or ""

    for line in description.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(("-", "*")):
            features.extend(_clean_strings([stripped.lstrip("-* ").strip()]))
        elif ":" in stripped and len(stripped) <= 120:
            features.extend(_clean_strings([stripped]))

        if len(features) >= FEATURE_LIMIT:
            break

    return _clean_strings(features, limit=FEATURE_LIMIT)


def _pricing_model(price: Any, is_free: bool | None = None, offers_iap: bool | None = None) -> str:
    numeric_price = None
    if isinstance(price, (int, float)):
        numeric_price = float(price)
    elif isinstance(price, str):
        text = price.strip().lower()
        if text in {"", "0", "0.0", "free"}:
            numeric_price = 0.0

    if offers_iap:
        return "freemium" if is_free is not False else "paid_with_iap"
    if is_free is True or numeric_price == 0.0:
        return "free"
    if is_free is False or (numeric_price is not None and numeric_price > 0):
        return "paid"
    return "unknown"


class AppleCompetitorClient:
    """Keyless App Store competitor data via iTunes Lookup and reviews RSS."""

    def __init__(self, country: str | None = None, timeout: int | None = None):
        self.country = (country or settings.app_store_country).lower()
        self.timeout = timeout or settings.request_timeout_seconds

    @with_retry(exceptions=(TransientAPIError, httpx.TransportError))
    def _get_json(self, url: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)
            if response.status_code >= 500:
                raise TransientAPIError(f"{response.status_code} from {url}")
            response.raise_for_status()
            return response.json()

    def fetch_details(self, app_id: str) -> dict:
        params = {"id": app_id, "country": self.country}
        try:
            data = self._get_json(APPLE_LOOKUP_URL, params=params)
        except (httpx.HTTPStatusError, TransientAPIError) as exc:
            raise CompetitorSourceUnavailableError(
                f"App Store lookup unavailable for app '{app_id}': {exc}"
            ) from exc

        results = data.get("results") or []
        if not results:
            raise CompetitorSourceUnavailableError(
                f"App Store lookup returned no result for app '{app_id}'."
            )

        item = results[0]
        screenshots = _clean_strings(
            _as_list(item.get("screenshotUrls")) + _as_list(item.get("ipadScreenshotUrls"))
        )
        offers_iap = bool(item.get("inAppPurchases"))
        price = item.get("price")

        return {
            "platform": Platform.APP_STORE,
            "store_app_id": str(item.get("trackId") or app_id),
            "name": item.get("trackName") or f"App Store app {app_id}",
            "developer": item.get("artistName"),
            "category": item.get("primaryGenreName"),
            "estimated_downloads": None,
            "rating": item.get("averageUserRating"),
            "rating_count": item.get("userRatingCount"),
            "pricing_model": _pricing_model(price, is_free=price == 0, offers_iap=offers_iap),
            "monetization_details": {
                "price": price,
                "formatted_price": item.get("formattedPrice"),
                "currency": item.get("currency"),
                "offers_in_app_purchases": offers_iap,
                "in_app_purchase_count": len(item.get("inAppPurchases") or []),
            },
            "screenshots": screenshots,
            "features": _extract_features(item.get("description"), item.get("features")),
        }

    def fetch_reviews(self, app_id: str, limit: int = DEFAULT_REVIEW_LIMIT) -> list[dict]:
        if limit <= 0:
            return []

        url = APPLE_REVIEWS_URL.format(country=self.country, app_id=app_id)
        try:
            data = self._get_json(url)
        except (httpx.HTTPStatusError, TransientAPIError) as exc:
            raise CompetitorSourceUnavailableError(
                f"App Store reviews unavailable for app '{app_id}': {exc}"
            ) from exc

        entries = data.get("feed", {}).get("entry") or []
        if isinstance(entries, dict):
            entries = [entries]

        reviews = []
        for entry in entries:
            if "im:rating" not in entry:
                continue
            reviews.append({
                "platform": Platform.APP_STORE,
                "author": entry.get("author", {}).get("name", {}).get("label"),
                "rating": _safe_int(entry.get("im:rating", {}).get("label")),
                "review_text": entry.get("content", {}).get("label"),
                "posted_at": _parse_datetime(entry.get("updated", {}).get("label")),
                "extracted_topics": {"source": "app_store_customer_reviews"},
            })
            if len(reviews) >= limit:
                break

        logger.info("Fetched {} App Store reviews for {}", len(reviews), app_id)
        return reviews


class GooglePlayCompetitorClient:
    """Google Play competitor data via gplay-scraper."""

    def __init__(self, country: str | None = None, lang: str = "en", scraper: Any | None = None):
        self.country = country or settings.google_play_country
        self.lang = lang
        self._scraper = scraper or self._build_scraper()

    def _build_scraper(self):
        try:
            from gplay_scraper import GPlayScraper
        except ModuleNotFoundError as exc:
            raise CompetitorSourceUnavailableError(
                "gplay-scraper is not installed; install project requirements to use Google Play competitor analysis."
            ) from exc
        return GPlayScraper()

    def fetch_details(self, app_id: str) -> dict:
        try:
            data = self._scraper.app_analyze(app_id, lang=self.lang, country=self.country)
        except Exception as exc:  # noqa: BLE001 - scraper exception types are not stable
            raise CompetitorSourceUnavailableError(
                f"Google Play details unavailable for app '{app_id}': {exc}"
            ) from exc

        if not data:
            raise CompetitorSourceUnavailableError(
                f"Google Play returned no details for app '{app_id}'."
            )

        offers_iap = bool(data.get("offersIAP") or data.get("offers_in_app_purchases"))
        is_free = data.get("free")
        price = data.get("price")
        screenshots = _clean_strings(_as_list(data.get("screenshots") or data.get("screenShots")))

        return {
            "platform": Platform.GOOGLE_PLAY,
            "store_app_id": str(data.get("appId") or app_id),
            "name": data.get("title") or f"Google Play app {app_id}",
            "developer": data.get("developer"),
            "category": data.get("genre") or data.get("genreId"),
            "estimated_downloads": _string_or_none(data.get("installs") or data.get("minInstalls")),
            "rating": data.get("score"),
            "rating_count": data.get("ratings") or data.get("reviews"),
            "pricing_model": _pricing_model(price, is_free=is_free, offers_iap=offers_iap),
            "monetization_details": {
                "price": price,
                "free": is_free,
                "offers_in_app_purchases": offers_iap,
                "contains_ads": data.get("containsAds") or data.get("adSupported"),
                "currency": data.get("currency"),
            },
            "screenshots": screenshots,
            "features": _extract_features(data.get("description") or data.get("summary")),
        }

    def fetch_reviews(self, app_id: str, limit: int = DEFAULT_REVIEW_LIMIT) -> list[dict]:
        if limit <= 0:
            return []

        try:
            raw_reviews = self._fetch_reviews_from_scraper(app_id, limit)
        except Exception as exc:  # noqa: BLE001
            raise CompetitorSourceUnavailableError(
                f"Google Play reviews unavailable for app '{app_id}': {exc}"
            ) from exc

        reviews = []
        for item in raw_reviews or []:
            reviews.append({
                "platform": Platform.GOOGLE_PLAY,
                "author": item.get("userName") or item.get("author"),
                "rating": _safe_int(item.get("score") or item.get("rating")),
                "review_text": item.get("text") or item.get("content"),
                "posted_at": _parse_datetime(item.get("at") or item.get("date")),
                "extracted_topics": {"source": "google_play_reviews"},
            })
            if len(reviews) >= limit:
                break

        logger.info("Fetched {} Google Play reviews for {}", len(reviews), app_id)
        return reviews

    def _fetch_reviews_from_scraper(self, app_id: str, limit: int) -> list[dict]:
        if hasattr(self._scraper, "reviews_analyze"):
            return self._scraper.reviews_analyze(
                app_id, count=limit, lang=self.lang, country=self.country
            )
        if hasattr(self._scraper, "reviews"):
            return self._scraper.reviews(app_id, count=limit, lang=self.lang, country=self.country)
        raise CompetitorSourceUnavailableError(
            "The installed gplay-scraper version does not expose a reviews method."
        )


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
